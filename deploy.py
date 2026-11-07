import json
import os
import argparse

STATE_FILE = "deployment_state.json"

ENVIRONMENTS = ["dev", "testing", "staging", "prod"]

DEFAULT_STATE = {
    env: {
        "active_version": "v1.0",
        "previous_version": None,
        "active_slot": "blue",
        "slots": {
            "blue": "v1.0",
            "green": None
        }
    }
    for env in ENVIRONMENTS
}


def load_state():
    """Read deployment information safely."""

    if not os.path.exists(STATE_FILE):
        return json.loads(json.dumps(DEFAULT_STATE))

    try:
        with open(STATE_FILE, "r") as file:
            content = file.read().strip()

            if not content:
                print("State file is empty. Initializing default state.")
                return json.loads(json.dumps(DEFAULT_STATE))

            return json.loads(content)

    except (json.JSONDecodeError, OSError):
        print("Invalid state file. Initializing default state.")
        return json.loads(json.dumps(DEFAULT_STATE))


def save_state(state):
    """Save deployment information safely."""

    temp_file = STATE_FILE + ".tmp"

    with open(temp_file, "w") as file:
        json.dump(state, file, indent=4)

    os.replace(temp_file, STATE_FILE)


def show_status(state):
    """Display the current version in each environment."""

    print("\n========== DEPLOYMENT STATUS ==========")

    for env, details in state.items():
        print(f"\nEnvironment: {env.upper()}")
        print("Active Version:", details["active_version"])
        print("Previous Version:", details["previous_version"])
        print("Active Slot:", details["active_slot"])

    print("\n=======================================")


def deploy(env, version, strategy, fail_health, auto_approve):
    """Deploy a new application version."""

    state = load_state()

    if env not in ENVIRONMENTS:
        print("Invalid environment!")
        return

    current = state[env]

    if current["active_version"] == version:
        print(f"Version {version} is already deployed.")
        return

    if not version.startswith("v"):
        print("Version must start with 'v' (example: v2.0)")
        return

    print("\n========== DEPLOYMENT STARTED ==========")
    print("Environment:", env.upper())
    print("New Version:", version)
    print("Strategy:", strategy.upper())
    print("Current Version:", current["active_version"])

    # Production approval gate
    if env == "prod" and not auto_approve:
        approval = input(
            "\nApprove production deployment? (yes/no): "
        ).strip().lower()

        if approval != "yes":
            print("Deployment cancelled: approval not granted.")
            return

    old_version = current["active_version"]

    # 1. Direct Deployment
    if strategy == "direct":

        print("\nDeploying application directly...")

        if fail_health:
            print("Health check FAILED!")
            print("Deployment stopped. Previous version remains active.")
            return

        current["previous_version"] = old_version
        current["active_version"] = version

    # 2. Blue-Green Deployment
    elif strategy == "blue-green":

        active_slot = current["active_slot"]

        inactive_slot = (
            "green" if active_slot == "blue" else "blue"
        )

        print(f"\nCurrent active slot: {active_slot}")
        print(f"Deploying {version} to {inactive_slot} slot...")

        current["slots"][inactive_slot] = version

        print("Testing the new slot...")

        if fail_health:
            print("Health check FAILED!")
            print("Keeping the old slot active.")
            return

        print("Health check PASSED!")
        print("Switching traffic to the new slot...")

        current["previous_version"] = old_version
        current["active_version"] = version
        current["active_slot"] = inactive_slot

        print("Traffic successfully switched.")

    # 3. Canary Deployment
    elif strategy == "canary":

        print("\nStarting Canary Deployment...")

        traffic_stages = [10, 25, 50, 100]

        for percentage in traffic_stages:

            print(f"\nSending {percentage}% traffic to {version}...")

            if fail_health and percentage == 25:
                print("Health check FAILED!")
                print("Stopping the canary release.")
                print("Rolling back to:", old_version)
                print("100% traffic remains on the old version.")
                return

            print(f"Health check PASSED at {percentage}% traffic.")

        current["previous_version"] = old_version
        current["active_version"] = version

        print("\nCanary deployment completed successfully.")

    else:
        print("Invalid deployment strategy!")
        return

    save_state(state)

    print("\nDeployment SUCCESSFUL!")
    print("Active Version:", current["active_version"])
    print("Previous Version:", current["previous_version"])
    print("========================================")


def rollback(env):
    """Restore the previous application version."""

    state = load_state()

    if env not in ENVIRONMENTS:
        print("Invalid environment!")
        return

    current = state[env]
    previous = current["previous_version"]

    if previous is None:
        print("No previous version available for rollback.")
        return

    print("\n========== ROLLBACK STARTED ==========")
    print("Current Version:", current["active_version"])
    print("Restoring Version:", previous)

    current["active_version"] = previous
    current["previous_version"] = None

    active_slot = current["active_slot"]

    if active_slot in current["slots"]:
        current["slots"][active_slot] = previous

    save_state(state)

    print("Rollback SUCCESSFUL!")
    print("Active Version:", current["active_version"])
    print("======================================")


def main():

    parser = argparse.ArgumentParser(
        description="Python CD Deployment Simulator"
    )

    parser.add_argument(
        "action",
        choices=["deploy", "status", "rollback"]
    )

    parser.add_argument(
        "--env",
        choices=ENVIRONMENTS
    )

    parser.add_argument(
        "--version"
    )

    parser.add_argument(
        "--strategy",
        choices=["direct", "blue-green", "canary"],
        default="direct"
    )

    parser.add_argument(
        "--fail-health",
        action="store_true",
        help="Simulate a failed health check"
    )

    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Skip manual production approval"
    )

    args = parser.parse_args()

    if args.action == "status":
        show_status(load_state())

    elif args.action == "deploy":

        if not args.env or not args.version:
            parser.error("deploy requires --env and --version")

        deploy(
            args.env,
            args.version,
            args.strategy,
            args.fail_health,
            args.auto_approve
        )

    elif args.action == "rollback":

        if not args.env:
            parser.error("rollback requires --env")

        rollback(args.env)


if __name__ == "__main__":
    main()