"""LevelUp_AruAI: learn Python with a Question Agent and a Teacher Agent."""
from .agents import Coordinator, QuestionAgent, TeacherAgent, Message, Question, AgentError
from .templates import TOPICS

__all__ = ["Coordinator", "QuestionAgent", "TeacherAgent", "Message", "Question", "AgentError", "TOPICS"]
__version__ = "1.0.0"
