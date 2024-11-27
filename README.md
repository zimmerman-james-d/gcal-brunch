# Summary
This is a tool designed to help groups find times for flexible meetings. It creates a message that can be pasted into the communication tool of your choice and allow for the use of emoji to vote for times that work for them.

## Setup
Install Python 3.10.6 or later.
Install Python Dependencies `pip install -r ./src/requirements.txt`

## Configuration
This script requires some configuration in order to work properly the first time.

### Google API
You will need to set up a google OAuth consent process and copy the generated json file:

https://developers.google.com/workspace/guides/configure-oauth-consent

To download an existing credentials file visit: https://console.cloud.google.com/apis/credentials and download the appropriate OAuth client.

### Preferences
There are 5 configurable preferences in the `./src/configuration/preferences.json` file:
- "EarliestStart": Hour as an integer in 24 hours.
- "LatestEnd": Hour as an integer in 24 hours.
- "LengthOfMeetingWindow": Number of days as an integer
- "IncludeNoAsOption": Boolean to enable or disable the `Unable to attend` option.
- "NoEmoji": Emoji as exptected by the end client for a user to indicate they are unable to attend.
### EMOJI LIST
The emoji list is based on Slack Emoji rules and assumes all Emoji are wrapped in `:`.


## TODO:
- Add Command Line functionality/inputs.
- Allow external sourcing of users.
- Handle expired 'token.json' file gracefully.

## Use
Update the ATTENDEES variable in the `gcal_options.py` script
Update the EARLIEST_MEETING_TIME variable in the `gcal_options.py` script
The script expects to be executed from the `src` directory.
Run the script with `python gcal_options.py`
