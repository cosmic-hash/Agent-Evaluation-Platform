"""One-shot subprocess entrypoint for an individual agent invocation.

This is process isolation, not a hostile-code sandbox. Production adapters should run in
an unprivileged container/microVM with network and filesystem policies.
"""
import json
import sys

from app.adapters import get_adapter


def main() -> None:
    request = json.load(sys.stdin)
    response = get_adapter(request["adapter_type"]).run(request["input"], request["config"])
    print(json.dumps(response.__dict__))


if __name__ == "__main__":
    main()
