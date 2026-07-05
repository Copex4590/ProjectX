# ============================================================================
# Project X
# File    : main.py
# Version : 0.3.0-alpha
# ============================================================================

from app.application import Application


def main():

    application = Application()

    return application.run()


if __name__ == "__main__":
    raise SystemExit(main())
