#!/bin/bash

# Define the source and destination directories
source_dir="/Users/cnShirLi/studyEN/sounds"
destination_dir="/Users/cnShirLi/flaskStudy/static/"

# Copy the "sounds" folder to the destination directory
rsync -av --ignore-existing "$source_dir" "$destination_dir"

rsync -av "/Users/cnShirLi/flaskStudy/data/review/" "/Users/cnShirLi/studyEN/user_data/review/"
