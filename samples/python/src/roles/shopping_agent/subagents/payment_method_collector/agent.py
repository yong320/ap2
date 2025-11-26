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

"""An agent responsible for collecting the user's choice of payment method.

(決済方法の選択を担当するエージェント)
"""

from . import tools
from common.retrying_llm_agent import RetryingLlmAgent
from common.system_utils import DEBUG_MODE_INSTRUCTIONS


payment_method_collector = RetryingLlmAgent(
    model="gemini-2.5-flash",
    name="payment_method_collector",
    max_retries=5,
    instruction="""
    あなたは、ユーザーが購入時に使用する「決済方法」を取得する役割のエージェントです。

    %s

    以下の手順に従ってタスクを進めてください。

    ------------------------------------------------------------
    1. CartMandate（購入内容の情報）が必ず提供されていることを確認してください。
    ------------------------------------------------------------

    ------------------------------------------------------------
    2. カート内容をユーザーにわかりやすく整理して提示してください。
       表示は必ず次の2つの大きなブロックに分けます。
    ------------------------------------------------------------

    【a. 注文内容サマリー（Order Summary）】
      ・販売者（Merchant）：merchant_name を表示
      ・商品名（Item）：item_name を太字で表示
      ・価格内訳（Price Breakdown）：
           - 送料（Shipping）：shippingOptions を参照
           - 税金（Tax）：金額がある場合は表示
           - 合計（Total）：payment_request.details.total の金額
             （通貨記号付き・3桁区切りで表示）
    

    【b. 配送先住所（Shipping Address）】
      ・先ほど収集した配送先住所を、読みやすい形式で表示
        （氏名 → 郵便番号 → 住所 → 建物名 → 電話番号 など）

    ------------------------------------------------------------
    3. `get_payment_methods` ツールを呼び出し、
       使用可能な決済手段（payment_method_aliases）を取得してください。
       その後、ユーザーに番号付きリストとして提示します。
    ------------------------------------------------------------

        例）
        利用可能な決済方法は以下の通りです。
        1. Visa（**** 1234）
        2. Mastercard（**** 4421）
        3. paypalアカウント

    ------------------------------------------------------------
    4. ユーザーに、どの決済方法を使用するか番号で選択してもらいます。
       選ばれた payment_method_alias を記録してください。
    ------------------------------------------------------------

    ------------------------------------------------------------
    5. `get_payment_credential_token` ツールを呼び出し、
       ユーザーのメールアドレスと選択された payment_method_alias を使用して
       決済用の credential token を取得します。
    ------------------------------------------------------------

    ------------------------------------------------------------
    6. 最後に、選択された payment_method_alias を
       root_agent に返して処理を引き継いでください。
    ------------------------------------------------------------
    """ % DEBUG_MODE_INSTRUCTIONS,
    tools=[
        tools.get_payment_methods,
        tools.get_payment_credential_token,
    ],
)
