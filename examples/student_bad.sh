#!/usr/bin/env bash
# Deliberately flawed example for testing partial marks.
user_name=$1
group_name=$2

groupadd "$group_name"
useradd "$user_name"
mkdir -p "/srv/$group_name"
chmod 0755 "/srv/$group_name"
