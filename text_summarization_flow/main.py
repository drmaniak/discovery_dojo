import sys

from flow import my_flow

shared = {"filepath": sys.argv[1]}
my_flow.run(shared)
