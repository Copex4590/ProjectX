# ============================================================================
# Project X
# File    : main.py
# Version : 0.3.1-alpha.1
# ============================================================================

from app.application import Application


def main():

    application = Application()

    return application.run()


if __name__ == "__main__":
    raise SystemExit(main())
