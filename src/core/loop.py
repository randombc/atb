from core.navigation import Navigator
from utilities.root import RootNode


def main_loop():
    navigator = Navigator()
    navigator.init(RootNode())

    while True:
        try:
            navigator.process()
        except KeyboardInterrupt:
            break
        except EOFError:
            break

    print('bye')
