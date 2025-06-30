import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from typing import Optional
from config import AI_MODEL

# ログ設定（必要に応じてレベルを DEBUG に変更可能）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)
class AIClient:
    """
    ユーザーの発言に対して、会話を盛り上げる返答を生成するクラス。
    """

    PROMPT_PATH = Path(__file__).resolve().parents[2] / "static" / "prompt.txt"

    def __init__(self, model: str = AI_MODEL, prompt_path: Optional[Path] = None):
        load_dotenv()
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        self.prompt_path = Path(prompt_path) if prompt_path else self.PROMPT_PATH
        logging.info(
            f"AIClient initialized with model: {model} and prompt: {self.prompt_path}"
        )

    def _load_prompt(self) -> str:
        try:
            return self.prompt_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read prompt template: {e}")
            return "以下は複数のユーザーの発言です。会話が盛り上がるよう、自然な返答をしてください。\n【ユーザー発言】:\n{user_message}\n"

    def create_response(self, user_message: str) -> str:
        """
        ユーザー全体の発言ログを要約する（興味・知識・スキルの傾向など）。
        """

        prompt_template = self._load_prompt()
        prompt = prompt_template.format(user_message=user_message)
        logger.info(f"Prompt sent to LLM: {prompt}")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            ai_text = response.choices[0].message.content.strip()
            logger.info("LLM response: %s", ai_text)
            return ai_text
        except Exception as e:
            logging.error(f"[✗] 返答生成失敗: {e}")
            return "すみません、AIが回答できませんでした。"
