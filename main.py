import argparse
from airhauler import AirHauler


def do_work(args):
    airhauler = AirHauler()

    airhauler.calculate_jobs()


def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    do_work(args)


if __name__ == '__main__':
    main()
