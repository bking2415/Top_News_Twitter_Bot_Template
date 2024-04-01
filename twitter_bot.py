from config import API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET, BEARER_TOKEN
import tweepy
import requests
import os
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
import datetime
# Download the stopwords list (if not already downloaded)
import nltk
from nltk.tokenize import word_tokenize

# Stop words
# nltk.download('punkt')
# nltk.download('stopwords')

# Twitter API credentials
consumer_key = API_KEY
consumer_secret = API_SECRET
access_token = ACCESS_TOKEN
access_token_secret = ACCESS_TOKEN_SECRET

# Authenticate with Twitter v1.0a
auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_token_secret)
api = tweepy.API(auth)

# Authenticate Twitter API v2 Client
bearer_token = BEARER_TOKEN

client = tweepy.Client(
    bearer_token=bearer_token,
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    access_token=access_token,
    access_token_secret=access_token_secret
    )

# Favorite categories for top news
news_dict = {
    'Tech': {'url': 'https://news.google.com/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US%3Aen'},
    'Gaming': {'url': 'https://news.google.com/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNREZ0ZHpFU0FtVnVLQUFQAQ?hl=en-US&gl=US&ceid=US%3Aen'},
    'NBA': {'url': 'https://news.google.com/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNRFZxZG5nU0FtVnVLQUFQAQ?hl=en-US&gl=US&ceid=US%3Aen'}
    }

# Function to summarize title to with set length
def summarize_title(title:str, extract_len:int=10):
    """
    Function to summarize the title of article extracted
    from the webpage using BeautifulSoup

    Args:
        title (str): the title of article
        extract_len (int): the constraint for the length of the article title

    Returns:
        str: summarized title of the article
    """
    # Check if the title has more than "n" words
    if len(title.split()) > (extract_len*2):
        # Tokenize the title
        words = word_tokenize(title)

        # Reduce the number of words (adjust as needed) by selecting the first and last few words
        summary_length =extract_len
        summary_words = words[:summary_length] + words[-summary_length:]

        # Summarized title using Extractive Summarization method
        summarized = " ".join(summary_words).replace(" ,", ",").replace(" '", "'").replace(" ?", "?").replace("‘ ", "‘").replace(" ’", "’")
    else:
        summarized = title
    # print(summarized)
    return summarized

# Function to fetch top news links from a given URL
def get_top_news(key:str, dictionary:dict, soup):
    """
    Function to fetch top news links from a given URL
    and stores additional information in dictionary.

    Args:
        key (str): category of news related to the article
        dictionary (dict): dictionary of topics and urls
        soup (Beautiful Soup object): Beautiful Soup object of the HTML document of  webpage

    Returns:
        dict: updated dictionary with title, sum_title, and link
    """
    # Google base URL
    base_url = 'https://news.google.com'
    
    # Extract first news link from the latest webpage
    link = soup.find('a', 'gPFEn', href=True)
    # Get title and link to most recent article
    dictionary[key]['title'] = link.text
    dictionary[key]['sum_title'] = summarize_title(link.text)
    dictionary[key]['link'] = base_url + link['href'][1:]
   
    return dictionary  # Return the top news link details by category

def convert_string_to_hours(split_string:list):
    """
    Function that converts strings to hours
    Examples:
        - '34 hours ago'
        - '10 minutes ago'
        - 'Yesterday'

    Args:
        split_string (list): list of split strings evaluated to convert to time (in hours)

    Returns:
        int: converted integer value from string
    """
    if "minutes" in split_string[0]:
        minutes = int(split_string[0].split()[0])
        hours = minutes // 60
        time_part = hours
    elif "days" in split_string[0]:
        days = int(split_string[0].split()[0])
        hours = days * 24
        time_part = hours
    else:
        try:
            time_part = int(split_string[0].split()[0])
        except ValueError:  # If time part is "Yesterday"
            time_part = 24
            split_string[0] = split_string[0].replace("Yesterday", "")  # Remove "Yesterday" from the string
    
    return time_part

def split_post_info(key:str, post_strings:list):
    """
    This funtion:
    - converts string to hours of related article urls
    - extract author name of related article urls

    Args:
        key (str): category of news related to the article
        post_strings (list):list of information for related article urls

    Returns:
        dictionary, pd.DataFrame: dictionary and DataFrame of post time and author sorted by post time (descending)
    """
    # New list to store dictionaries
    modified_dicts = []

    # Convert days to hours and split strings by "ago"
    for string in post_strings:
        parts = string.split(" ago")
    
        time_part = convert_string_to_hours(parts)

        # Extract the name part
        try:
            name_part = parts[1].split("By")[0].strip()
            if name_part == "":
                name_part = "unknown"
        except IndexError:  # If time part is "Yesterday"
            name_part = parts[0].split("By")[0].strip()
            if name_part == "":
                name_part = "unknown"
        
        # Create a dictionary
        data_dict = {"time": time_part, "author": name_part}
        modified_dicts.append(data_dict)

    # Sort the list of dictionaries by "time" in descending order then "name" in ascending order
    sorted_dicts = sorted(modified_dicts, key=lambda x: (-x["time"], x["author"]))

    # convert to DataFrame
    df = pd.DataFrame(sorted_dicts)
    
    # Add a header row to the DataFrame
    df.columns = [key, ""]
    
    # Create a DataFrame for the row above column names
    header_row = pd.DataFrame([["Prior Posts Time (hours ago)", "Author"]], columns=df.columns)

    # Concatenate the header row with the original DataFrame
    df = pd.concat([header_row, df], ignore_index=True)
    
    return sorted_dicts, df

# Function to fetch 3 latest post about top news link
def get_posts_info(key:str, dictionary:dict, soup):
    """
    Function to fetch 3 latest post about top news link

    Args:
        key (str): category of news related to the article
        dictionary (dict): dictionary of topics and urls
        soup (Beautiful Soup object): Beautiful Soup object of the HTML document of webpage

    Returns:
        dict: updated dictionary with sorted_dicts and df
    """
    posts_info = []

    # Extract top 3 news post related to main article from the webpage
    for post in soup.find_all('div', 'UOVeFe Jjkwtf'):
        posts_info.append(post.text)
    # Return formatted top 3 posts    
    dictionary[key]['sorted_dicts'], dictionary[key]['df'] = split_post_info(key, posts_info[:3]) 
    # print(dictionary[key]['table'])
        
    return dictionary # Return updated dictionary

def generate_table_image(df:pd.DataFrame):
    """
    Function creates a table using Matplotlib 
    of the 3 latest post about top news link
    and saves the table as a .png file

    Args:
        df (pd.DataFrame): DataFrame of top 3 news post related to main article from the webpage
    """
    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(1600/100, 900/100), dpi=100)
    
    # Create a custom table
    colors = ['lemonchiffon', 'lemonchiffon', 'lightgreen', 'lightgreen', 'lightcoral', 'lightcoral']
    ax.table(cellText=df.values, colLabels=df.columns, loc='center', cellLoc='center', colColours=colors, fontsize=1000)

    # Remove axis
    ax.axis('off')  # Turn off axis
    
    # Add title
    ax.set_title('Most Recent Articles by Category', fontsize=20, fontweight='bold')
    
    # fig.tight_layout()  # Adjust layout

    # Save the plot as a .png file
    fig.savefig('table.png')
    
    # Show the plot (optional)
    # plt.show()

# Function to tweet multiple titles in one post
def tweet_titles_in_one_post(dictionary):
    """
    This function:
    - tweet titles and categories of articles in one post
    - attached media of table analytics of of the 3 latest post about top news link
    
    Args:
        dictionary (dict): dictionary of topics and urls
        
    Returns:
        dict: Response of tweet information
    """
    # Get the current date and time
    now = datetime.datetime.now()
    
    # Get the day of the week (Monday=0, Sunday=6) and convert it to the corresponding name
    day_of_week = datetime.datetime.now().strftime("%A")

    # Get the time of the day and determine if it's morning, afternoon, evening, or night
    hour = now.hour
    if 7 <= hour < 12:
        time_of_day = "morning"
    elif 12 <= hour < 17:
        time_of_day = "afternoon"
    elif 17 <= hour < 20:
        time_of_day = "evening"
    else:
        time_of_day = "night"

    message = f"Top News for {day_of_week} {time_of_day}:\n"
    for key in dictionary:
            message += f"- {key} : {dictionary[key]['sum_title']}\n"
    message += "And check out these analytics!" 
    # print(message)
    # Upload the image
    media = api.media_upload("table.png")
    # Tweet the message along with the plot
    tweet = client.create_tweet(text=message, media_ids=[media.media_id])
    
    return tweet

def quote_tweet_post_with_links(dictionary:dict, tweet:requests.Response):
    """
    Funtion that quote tweets previous tweet and attaches 
    URLs of each article to the post

    Args:
        dictionary (dict): dictionary of topics and urls
        tweet (requests.Response): Twitter post that will be quote tweeted

    Returns:
        dict: Response of quote tweet information
    """
    message = f"Check out the links to the Articles:\n"
    for key in dictionary:
            message += f"- {key} : {dictionary[key]['link']}\n" 
    # print(message)
    # Quote tweet post with links in message
    quote_tweet = client.create_tweet(text=message, quote_tweet_id=tweet.data['id'])
    return quote_tweet

# Main function to fetch and tweet news links
def main(dictionary:dict):
    """
    Main function that executes the sequence of the code

    Args:
        dictionary (dict): dictionary of topics and urls
    """
    df = pd.DataFrame()
    for category in dictionary:
        response = requests.get(dictionary[category]['url'])
        soup = BeautifulSoup(response.text, 'html.parser')
        # Get title, summarized title, and link to top news
        dictionary = get_top_news(category, dictionary, soup)
        # Get most recent posts about top news topic
        dictionary = get_posts_info(category, dictionary, soup)
        # Combine DataFrame objects horizontally along the x axis
        df = pd.concat([df, dictionary[category]['df']], axis=1)
    # Covert DataFrame into table image    
    generate_table_image(df)
    # Tweet the posts
    # Initialize the value
    len = 10

    while True:
        # Subtract 1 from the value
        len -= 1
        
        # Dynamically check if the post meets character length guidelines
        try:
            tweet = tweet_titles_in_one_post(dictionary)
            print("Tweet posted successfully! \n", tweet.data['text'])
            break  # Exit the loop if successful
        except Exception as e:
            print("Error posting tweet:", e)
            # Update the summarized title
            for category in dictionary:
                dictionary[category]['sum_title'] = summarize_title(dictionary[category]['title'], extract_len=len)

        # Check if the value has reached 0
        if len == 0:
            print("Value reached 0. Exiting the loop.")
            break
    
    # Quote tweet post with links
    try:
        quote_tweet = quote_tweet_post_with_links(dictionary, tweet)
        print("Quote tweet posted successfully! \n", quote_tweet.data['text'])
    except Exception as e:
        print("Error posting quote tweet:", e)
            
if __name__ == "__main__":
    main(news_dict)