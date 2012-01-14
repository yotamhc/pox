#!/bin/bash

find . -name "*py" \! -path "./pox/lib/anteater/*" \! -path "./pox/lib/networkx/*" | xargs grep --color=auto $@
