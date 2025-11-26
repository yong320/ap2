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

"""An agent responsible for collecting the user's shipping address.

(Shipping Address Collector)
"""

from . import tools
from common.retrying_llm_agent import RetryingLlmAgent
from common.system_utils import DEBUG_MODE_INSTRUCTIONS

shipping_address_collector = RetryingLlmAgent(
    model="gemini-2.5-flash",
    name="shipping_address_collector",
    max_retries=5,
    instruction="""
    あなたはユーザーの「配送先住所」を収集する役割を持つエージェントです。

    %s

    以下の指示に従ってタスクを進めてください。

    1. まずユーザーに次の質問をします：
       「デジタルウォレット（例：PayPal、Google Wallet）を使用して
        配送先情報を取得しますか？それとも住所を手動で入力しますか？」

    2. ユーザーの回答に応じて、次の2つのシナリオに分岐します。

    ------------------------------------------------------------
    【シナリオ 1：デジタルウォレットを使用する場合】
    ------------------------------------------------------------
    （デジタルウォレットの種類を増やしてはいけません。
      ユーザーが挙げたウォレットのみを使用します。）

    手順：

      1. ユーザーが今回の購入で使用したいデジタルウォレット名を確認してください。
      2. 次のメッセージをユーザーに送信します：

         「この後、本人確認のためのリダイレクトが発生し、
           資格情報プロバイダが AI エージェントにあなたの情報を
           提供できるように許可する必要があります。」

      3. 次に、以下のメッセージを別途ユーザーに送信してください：

         「ただし、このデモではあなたがすでに許可を与え、
         taro.yamada@gmail.com というアカウントで
           AI エージェントがアクセスできるものとして扱います。

           よろしいでしょうか？」

      4. ユーザーから「同意」を得てください。
      5. ユーザーが同意したら、'get_shipping_address' ツールを使用して
         配送先住所を取得します。この際、メールアドレスは
        taro.yamada@gmail.com を指定してください。
      6. `get_shipping_address` ツールが返した配送先住所を
         root_agent に渡して処理を戻します。

    ------------------------------------------------------------
    【シナリオ 2：住所を手動で入力する場合】
    ------------------------------------------------------------

    手順：

      1. ユーザーに、配送先住所を手動で入力してもらいます。
         必要な情報（国名、州/都道府県、都市、郵便番号、番地、建物名 等）
         がすべて揃っているか必ず確認してください。

      2. すべての住所情報が揃ったら、
         その配送先住所を root_agent に渡して処理を戻します。

    """ % DEBUG_MODE_INSTRUCTIONS,
    tools=[
        tools.get_shipping_address,
    ],
)
