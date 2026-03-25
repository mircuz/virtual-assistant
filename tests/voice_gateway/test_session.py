from uuid import uuid4
from voice_gateway.conversation.session import Session, SessionManager


def test_session_creation():
    s = Session(shop_id=uuid4(), shop_config={"name": "Salon Bella"})
    assert s.session_id is not None
    assert s.customer is None
    assert len(s.history) == 0


def test_session_add_turns():
    s = Session(shop_id=uuid4(), shop_config={"name": "Test"})
    s.add_user_turn("Ciao")
    s.add_assistant_turn("Benvenuto!")
    assert len(s.history) == 2
    assert s.history[0]["role"] == "user"
    assert s.history[1]["role"] == "assistant"


def test_session_history_sliding_window():
    s = Session(shop_id=uuid4(), shop_config={"name": "Test"}, max_history=4)
    for i in range(10):
        s.add_user_turn(f"msg {i}")
        s.add_assistant_turn(f"reply {i}")
    assert len(s.history) == 4  # sliding window


def test_session_manager_lifecycle():
    mgr = SessionManager()
    sid = mgr.create_session(shop_id=uuid4(), shop_config={"name": "Test"})
    session = mgr.get_session(sid)
    assert session is not None
    mgr.end_session(sid)
    assert mgr.get_session(sid) is None
