# ============================================================================
# Project X
# File    : main.py
# Version : 0.2.0-rc1
# ============================================================================

from app.application import Application


def main():

    application = Application()

    return application.run()


if __name__ == "__main__":
    raise SystemExit(main())
