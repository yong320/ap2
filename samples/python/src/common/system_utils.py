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

"""Helper functions related to the system."""

DEBUG_MODE_INSTRUCTIONS = """
    これは非常に重要です。エージェントまたはユーザーが詳細な説明を求めた場合、または debug_mode が True の場合は、次のルールに従ってください。
    1. 新しいタスクを開始する際は、あなたがどのようなエージェントであり、何を行うのか、使用するツール、そして委任するエージェントについて説明してください。
    2. タスクの進行中は、現在何をしているか、これまでに何を行ったか、次に何をする予定かを定期的に報告してください。
    3. 別のエージェントに処理を委任する場合は、そのエージェントやツールにも詳細モードでの応答を求めてください。
    4. タスク中にデータを送受信する場合は、そのデータを明確かつ整った形式で表示してください。英語で要約してはいけません。JSON などをそのままの形で示してください。
    5. この 4 のルールは非常に重要なので繰り返します。タスク中にデータを作成・送信・受信した場合は、必ずフォーマット済みの JSON などでそのまま表示し、英語の要約をしてはいけません。
 """
