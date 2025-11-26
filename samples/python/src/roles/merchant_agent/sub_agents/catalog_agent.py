# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A sub-agent that offers items from its 'catalog'.

This agent fabricates catalog content based on the user's request.
"""

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any

from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import DataPart
from a2a.types import Part
from a2a.types import Task
from a2a.types import TextPart
from google import genai
from pydantic import ValidationError

from .. import storage
from ap2.types.mandate import CART_MANDATE_DATA_KEY
from ap2.types.mandate import CartContents
from ap2.types.mandate import CartMandate
from ap2.types.mandate import INTENT_MANDATE_DATA_KEY
from ap2.types.mandate import IntentMandate
from ap2.types.payment_request import PaymentDetailsInit
from ap2.types.payment_request import PaymentItem
from ap2.types.payment_request import PaymentMethodData
from ap2.types.payment_request import PaymentOptions
from ap2.types.payment_request import PaymentRequest
from common import message_utils
from common.system_utils import DEBUG_MODE_INSTRUCTIONS


async def find_items_workflow(
    data_parts: list[dict[str, Any]],
    updater: TaskUpdater,
    current_task: Task | None,
) -> None:
  """Finds products that match the user's IntentMandate."""
  llm_client = genai.Client()

  intent_mandate = message_utils.parse_canonical_object(
      INTENT_MANDATE_DATA_KEY, data_parts, IntentMandate
  )
  intent = intent_mandate.natural_language_description
  prompt = f"""
        Based on the user's request for '{intent}', your task is to generate 3
        complete, unique and realistic PaymentItem JSON objects.

        You MUST exclude all branding from the PaymentItem `label` field.
        The items will later be compared based on price level and features such
        as absorbency and leak protection, so make each label descriptive enough
        (e.g. normal / high absorbency, premium, jumbo pack, etc.).

    %s
        """ % DEBUG_MODE_INSTRUCTIONS

  llm_response = llm_client.models.generate_content(
      model="gemini-2.5-flash",
      contents=prompt,
      config={
          "response_mime_type": "application/json",
          "response_schema": list[PaymentItem],
      }
  )
  try:
    items: list[PaymentItem] = llm_response.parsed

    current_time = datetime.now(timezone.utc)
    item_count = 0
    for item in items:
      item_count += 1
      await _create_and_add_cart_mandate_artifact(
          item, item_count, current_time, updater
      )
    risk_data = _collect_risk_data(updater)
    updater.add_artifact([
        Part(root=DataPart(data={"risk_data": risk_data})),
    ])
    await updater.complete()
  except ValidationError as e:
    error_message = updater.new_agent_message(
        parts=[Part(root=TextPart(text=f"Invalid CartMandate list: {e}"))]
    )
    await updater.failed(message=error_message)
    return


def _infer_product_features(item: PaymentItem, item_count: int) -> dict[str, str]:
  """Infer simple product features (for comparison) from the item.

  The result is stored into CartContents.product_features so that the shopping
  agent can later compare items like:
    - 価格レベル（高・中・低）
    - 吸水性（高・中・普通・非常に高い など）
    - 横漏れしやすさ（横漏れしにくい・標準的）
  """
  # 基本はラベルのテキストから簡単に推論する
  label = getattr(item, "label", "") or ""
  label_lower = label.lower()

  # 価格レベル：
  # ここではサンプルとして item_count ベースで簡単に決める。
  # 必要であれば金額から算出するロジックに差し替え可能。
  if item_count == 1:
    price_level = "中"
  elif item_count == 2:
    price_level = "低"
  else:
    price_level = "高"

  # 吸水性
  if "超吸水" in label or "超吸収" in label or "プレミアム" in label or "premium" in label_lower:
    absorbency = "非常に高い"
  elif "高吸水" in label or "高吸収" in label or "夜用" in label:
    absorbency = "高い"
  else:
    absorbency = "普通"

  # 横漏れしにくさ
  if "フィット" in label or "ガード" in label or "プレミアム" in label:
    leak = "横漏れしにくい"
  else:
    leak = "標準的"

  # ここでは 3 つのシンプルな属性だけを返す
  return {
      "price_level": price_level,        # 例: "低", "中", "高"
      "absorbency": absorbency,         # 例: "普通", "高い", "非常に高い"
      "leak_protection": leak,          # 例: "横漏れしにくい", "標準的"
  }


def _get_merchant_name_for_item(item_count: int) -> str:
  """Map item index to a merchant name (A社 / B社 / C社)."""
  merchant_map = {
      1: "A社",
      2: "B社",
      3: "C社",
  }
  return merchant_map.get(item_count, "A社")


async def _create_and_add_cart_mandate_artifact(
    item: PaymentItem,
    item_count: int,
    current_time: datetime,
    updater: TaskUpdater,
) -> None:
  """Creates a CartMandate and adds it as an artifact.

  In addition to the main item, this also adds a second PaymentItem to
  `display_items` that encodes product features such as price level,
  absorbency and leak protection, so that other agents can easily read
  and compare them.
  """
  # 先推論商品特征（価格レベル・吸水性・横漏れしやすさ など）
  merchant_name = _get_merchant_name_for_item(item_count)
  product_features = _infer_product_features(item, item_count)

  # 特征字符串（写在第二个 display_item 的 label 里）
  # 例）「特徴: 価格=中 / 吸水性=高い / 横漏れ=横漏れしにくい」
  features_label = (
      f"特徴: 価格={product_features['price_level']} / "
      f"吸水性={product_features['absorbency']} / "
      f"横漏れ={product_features['leak_protection']}"
  )

  # 为了不影响合计金额，特征项金额设为 0，currency 延用原金额
  feature_amount = item.amount.model_copy(update={"value": 0})

  feature_item = PaymentItem(
      label=features_label,
      amount=feature_amount,
  )

  payment_request = PaymentRequest(
      method_data=[
          PaymentMethodData(
              supported_methods="CARD",
              data={
                  "network": ["visa", "mastercard", "paypal", "amex"],
              },
          )
      ],
      details=PaymentDetailsInit(
          id=f"order_{item_count}",
          # 主商品 + 特征条目
          display_items=[item, feature_item],
          total=PaymentItem(
              label="Total",
              amount=item.amount,
          ),
      ),
      options=PaymentOptions(request_shipping=True),
  )

  cart_contents = CartContents(
      id=f"cart_{item_count}",
      user_cart_confirmation_required=True,
      payment_request=payment_request,
      cart_expiry=(current_time + timedelta(minutes=30)).isoformat(),
      merchant_name=merchant_name,
      # 如果 CartContents 有 product_features 字段，也可以在这里挂上：
      # product_features=product_features,
  )

  cart_mandate = CartMandate(contents=cart_contents)

  storage.set_cart_mandate(cart_mandate.contents.id, cart_mandate)
  await updater.add_artifact([
      Part(
          root=DataPart(data={CART_MANDATE_DATA_KEY: cart_mandate.model_dump()})
      )
  ])


def _collect_risk_data(updater: TaskUpdater) -> dict:
  """Creates a risk_data in the tool_context."""
  # This is a fake risk data for demonstration purposes.
  risk_data = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...fake_risk_data"
  storage.set_risk_data(updater.context_id, risk_data)
  return risk_data
