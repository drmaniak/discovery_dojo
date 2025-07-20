from pocketflow import Flow

from nodes.idea_generation import AnswerNode, GetQuestionNode


def create_qa_flow():
    """Create and return a simple question-answering flow (legacy)."""
    get_question_node = GetQuestionNode()
    answer_node = AnswerNode()

    get_question_node >> answer_node

    return Flow(start=get_question_node)
