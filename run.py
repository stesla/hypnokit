import sys

from hypnokit import Screen, Script


script = Script.load(sys.argv[1])
Screen(script).run()
