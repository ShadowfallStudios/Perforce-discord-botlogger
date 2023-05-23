import subprocess
import time
from os.path import abspath, dirname, join
import configparser
import sys
import os

from discord_webhooks import DiscordWebhooks

config_path = join(dirname(abspath(__file__)), "config.ini")

class Change():
  def __init__(self, change_header, content):
    split = change_header.split(" ")
    self.num = split[1]
    self.date = split[3]
    self.time = split[4]
    self.user = split[6]
    self.content = content

class PerforceLogger():
    def __init__(self, webhook_url, repository):
      self.webhook_url = webhook_url
      self.repository = repository

    def p4_fetch(self, max):
      """ Fetches the changes  """
      p4_changes = subprocess.Popen(f'p4 changes -t -m {max} -s submitted -e {sys.argv[1]} -l {self.repository}', stdout=subprocess.PIPE, shell=True)
      #Get the result from the p4 command
      return p4_changes.stdout.read().decode('ISO-8859-1')

    def regroup_changes(self, output):
      """ Makes a list with all the changes """
      changes = [] #Contains the change strings (one string per change)

      #If there are changes the string is not empty
      if(len(output) > 0):
        last_num_str = "" #this string will hold the first change number
        lines = output.splitlines() #split the strings by new line
        str_header = ""
        str_content_buffer = [] # this temporary buffer will contain each line of a change
        for l in lines:
          if(l.startswith('Change')): #If we see the word change (caracteristic of p4 changes), we close and open the buffer
            if(len(str_content_buffer) > 0): #Append the changes array with the last registered strings (closing change)
              changes.append(Change(str_header, ''.join(str_content_buffer)))
            else: # Only happens on first occurence: save the first change number as it is the most recent
              last_num_str = l.split(" ")[1]
            str_header = l
            str_content_buffer = [] # Start with a fresh buffer
          else: #Applies to other lines (content)
            str_content_buffer.append(l+"\n") #Add the current line
        # --- end of for loop ---

        #Last line closing
        changes.append(Change(str_header, ''.join(str_content_buffer)))

        # Also affect the last num
        if(last_num_str != ""): # Affect the last change number to the config file
          last_num = int(last_num_str)

      return changes

    def check_post_changes(self, signature=""):
      """ Posts each changes to the Discord server using the provided webhook. """
      changes_as_str = self.p4_fetch(max=1)
      changes = self.regroup_changes(changes_as_str)
      for payload in reversed(changes):
        if(payload != ''):
          user = payload.user.split("@")[0]
          message = DiscordWebhooks(self.webhook_url)
          message.set_author(name=f"@{user} : new submit" )
          message.set_content(color=0x51D1EC, description= f"`#{payload.num}`  - {payload.time} {payload.date} \n```fix\n{payload.content.lstrip()}``` ")
          message.set_footer(text=f"{signature}", ts=True)
          message.send()
          print("Sent payload")
        time.sleep(0.1) #sleep 0.1 second to avoid sending too much messages at once

if __name__ == "__main__":
  if (len(sys.argv) <= 1):
    print("Changelist number not provided as arg")
    quit()

  # Read config parameters and perform the checks
  config = configparser.ConfigParser()
  config.read(config_path)

  #Read config
  os.environ['P4USER'] = config['Perforce']['user']
  DISCORD_WEBHOOK_URL = config['Discord']['webhook']
  P4_TARGET = config['Perforce']['target']
  SIGNATURE = config['ApplicationSettings']['signature']

  #Init logger
  logger = PerforceLogger(DISCORD_WEBHOOK_URL, repository=P4_TARGET)

  #Perform checks - this line can be looped with a time.sleep(SECONDS) in case you don't use a scheduler
  logger.check_post_changes(signature=SIGNATURE)