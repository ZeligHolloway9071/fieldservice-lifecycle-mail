import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.fieldservice_email import InfraiClient, WorkOrder, publish_lifecycle_template


def main() -> None:
    recipient = sys.argv[1] if len(sys.argv) > 1 else "dispatcher@example.com"
    order = WorkOrder("WO-1042", "Mina", "scheduled", 2, recipient)
    result = publish_lifecycle_template(InfraiClient(), order)
    print({"template": result, "work_order": order.work_order_id, "recipient": order.recipient})


if __name__ == "__main__":
    main()
