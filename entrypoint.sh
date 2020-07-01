#!/bin/bash
wait-for-it postgresql:5432 -t 60
exec $*