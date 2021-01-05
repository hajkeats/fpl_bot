### FPL Messenger bot

This fpl_bot is an AWS lambda backed Facebook messenger bot that reports on the fixtures and results of a 
[fantasy premier league](https://fantasy.premierleague.com/) (FPL) head-to-head league.

Terraform is used to create the lambda, and setup a cron job that triggers the python code to run at 9:30AM everyday.
The bot then reports fixtures, or results and a link to the updated table depending on values given in the FPL API.

Unlike conventional messenger chatbots, this bot requires a regular account rather than a page, so that it can be added 
to a group chat. Each time it is run, it simply logs in and sends messages to the chat, without reading or listening for
responses.

> Note: Currently [fbchat](https://github.com/fbchat-dev/fbchat) is used, which is now unmaintained. Currently a bug 
> exists in the pypi release, meaning the login function included in the lambda source code requires a hacky workaround.

## Setup

> Note: You will need a fantasy premier league account, and a team in part of a head-to-head league to run this bot.

Create a facebook account for the bot, making note of the email and password.

Add the account to a facebook group chat of your choosing.

While logged in as the bot, navigate to the group chat in messenger. Make note of the thread id, which can be found in 
the url like `https://www.facebook.com/messages/t/<THREAD_ID>/`

Next, clone the repository. You'll want to use `--recurse-submodules` when cloning to get everything.

This repository contains a submodule with a branch of a repo for lambda deployment found 
[here](https://github.com/hajkeats/python_lambda_template). As such, many of the following instructions are copied from 
that repo.

Install [Terraform](https://www.terraform.io/).

Install the version of python you intend to use as runtime. This is tested and working with python3.8. You'll also need
`venv` which maybe shipped with your version of python, depending on how python is installed!

> To test that you have venv try `python3.8 -m venv test_venv`. A virtualenv called 'test_venv' should be created if you
> have it!

Export your AWS credentials as environment variables. As I'm using ubuntu, I've added mine to my `~/.bashrc`.
```
export AWS_ACCESS_KEY_ID="<ACCESS KEY>"
export AWS_SECRET_ACCESS_KEY="<SECRET KEY>"
```

## Deployment

From inside the 'terraform' directory run the following commands to deploy the code:

> Note: enter variable values when prompted - the facebook_email, facebook_password and thread_id values are those you 
> made note of from the setup earlier. fpl_email and fpl_password are your FPL details.
```
terraform init
terraform apply
# When prompted, type 'yes' and hit enter
```
This should create a lambda within AWS. Testing from the AWS console should result in a message in the groupchat if 
today is the start of a new FPL gameweek, or the day after one has finished!
