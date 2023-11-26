from collections import Counter
import json
import os
import sys

from secret import get_auth


def break_combined_weeks(combined_weeks):
    """
    Breaks combined weeks into separate weeks.
    
    Args:
        combined_weeks: list of tuples of weeks to combine
        
    Returns:
        tuple of lists of weeks to be treated as plus one and minus one
    """
    plus_one_week = []
    minus_one_week = []

    for week in combined_weeks:
        if week[0] < week[1]:
            plus_one_week.append(week[0])
            minus_one_week.append(week[1])
        else:
            minus_one_week.append(week[0])
            plus_one_week.append(week[1])

    return plus_one_week, minus_one_week

def get_msgs_df_info(df):
    msgs_count_dict = df.user.value_counts().to_dict()
    replies_count_dict = dict(Counter([u for r in df.replies if r != None for u in r]))
    mentions_count_dict = dict(Counter([u for m in df.mentions if m != None for u in m]))
    links_count_dict = df.groupby("user").link_count.sum().to_dict()
    return msgs_count_dict, replies_count_dict, mentions_count_dict, links_count_dict



def get_messages_dict(msgs):
    msg_list = {
            "msg_id":[],
            "text":[],
            "attachments":[],
            "user":[],
            "mentions":[],
            "emojis":[],
            "reactions":[],
            "replies":[],
            "replies_to":[],
            "ts":[],
            "links":[],
            "link_count":[]
            }


    for msg in msgs:
        if "subtype" not in msg:
            try:
                msg_list["msg_id"].append(msg["client_msg_id"])
            except:
                msg_list["msg_id"].append(None)
            
            msg_list["text"].append(msg["text"])
            msg_list["user"].append(msg["user"])
            msg_list["ts"].append(msg["ts"])
            
            if "reactions" in msg:
                msg_list["reactions"].append(msg["reactions"])
            else:
                msg_list["reactions"].append(None)

            if "parent_user_id" in msg:
                msg_list["replies_to"].append(msg["ts"])
            else:
                msg_list["replies_to"].append(None)

            if "thread_ts" in msg and "reply_users" in msg:
                msg_list["replies"].append(msg["replies"])
            else:
                msg_list["replies"].append(None)
            
            if "blocks" in msg:
                emoji_list = []
                mention_list = []
                link_count = 0
                links = []
                
                for blk in msg["blocks"]:
                    if "elements" in blk:
                        for elm in blk["elements"]:
                            if "elements" in elm:
                                for elm_ in elm["elements"]:
                                    
                                    if "type" in elm_:
                                        if elm_["type"] == "emoji":
                                            emoji_list.append(elm_["name"])

                                        if elm_["type"] == "user":
                                            mention_list.append(elm_["user_id"])
                                        
                                        if elm_["type"] == "link":
                                            link_count += 1
                                            links.append(elm_["url"])


                msg_list["emojis"].append(emoji_list)
                msg_list["mentions"].append(mention_list)
                msg_list["links"].append(links)
                msg_list["link_count"].append(link_count)
            else:
                msg_list["emojis"].append(None)
                msg_list["mentions"].append(None)
                msg_list["links"].append(None)
                msg_list["link_count"].append(0)
    
    return msg_list

def from_msg_get_replies(msg):
    replies = []
    if "thread_ts" in msg and "replies" in msg:
        try:
            for reply in msg["replies"]:
                reply["thread_ts"] = msg["thread_ts"]
                reply["message_id"] = msg["client_msg_id"]
                replies.append(reply)
        except:
            pass
    return replies

def msgs_to_df(msgs):
    msg_list = get_messages_dict(msgs)
    df = pd.DataFrame(msg_list)
    return df

def process_msgs(msg):
    '''
    select important columns from the message
    '''

    keys = ["client_msg_id", "type", "text", "user", "ts", "team", 
            "thread_ts", "reply_count", "reply_users_count"]
    msg_list = {k:msg[k] for k in keys}
    rply_list = from_msg_get_replies(msg)

    return msg_list, rply_list

def get_messages_from_channel(channel_path):
    '''
    get all the messages from a channel        
    '''
    channel_json_files = os.listdir(channel_path)
    channel_msgs = [json.load(open(channel_path + "/" + f)) for f in channel_json_files]

    nloop = len(channel_msgs)
    df = pd.concat([pd.DataFrame(get_messages_dict(msgs)) for msgs in channel_msgs])
    print(f"Number of messages in channel: {len(df)}")
    
    return df


def convert_2_timestamp(column, data):
    """convert from unix time to readable timestamp
        args: column: columns that needs to be converted to timestamp
                data: data that has the specified column
    """
    if column in data.columns.values:
        timestamp_ = []
        for time_unix in data[column]:
            if time_unix == 0:
                timestamp_.append(0)
            else:
                a = datetime.datetime.fromtimestamp(float(time_unix))
                timestamp_.append(a.strftime('%Y-%m-%d %H:%M:%S'))
        return timestamp_
    else: print(f"{column} not in data")

def slack_parser(path, channel):
    """ parse slack data to extract useful informations from the json file
    step of execution
    1. Import the required modules
    2. read all json file from the provided path
    3. combine all json files in the provided path
    4. extract all required informations from the slack data
    5. convert to dataframe and merge all
    6. reset the index and return dataframe
    """
    users = pd.read_json(cfg.userfile)[['id', 'real_name']]
    combined = []
    dfall = pd.DataFrame()

    # specify path to get json files
    try:
        for json_file in glob.glob(f"{path}*.json"):
            with open(json_file, 'r') as slack_data:
                combined.append(slack_data)
        print("Total Days ", len(combined))
    except Exception as e:
        print(e)
        print('Parser stopped!!')

    # loop through jsonfiles
    print('parser starting..')
    for i in combined:
        slack_data = json.load(open(i.name, 'r', encoding="utf8"))

        slack_id, student_id, week, msg_content, sender_id, time_msg, msg_dist, time_thread_st, reply_users, \
        reply_count, reply_users_count, tm_thread_end = [],[],[],[],[],[],[],[],[],[],[], []
        # print('comboned')
        for row in slack_data:
            if 'bot_id' in row.keys():
                print('Bot ID found')
                continue
            else:
                try:
                    slack_id.append(row['user'])
                    student_id.append(row['user'])
                    week.append(row['type'])
                    msg_content.append(row['text'])
                    if 'user' in row.keys(): sender_id.append(row['user'])
                    else: sender_id.append('Not provided')
                    time_msg.append(row['ts'])
                    if 'blocks' in row.keys() and len(row['blocks'][0]['elements'][0]['elements']) != 0 :
                         msg_dist.append(row['blocks'][0]['elements'][0]['elements'][0]['type'])
                    else: msg_dist.append('reshared')
                    if 'thread_ts' in row.keys():
                        time_thread_st.append(row['thread_ts'])
                    else:
                        time_thread_st.append(row['ts'])
                    if 'reply_users' in row.keys(): reply_users.append(",".join(row['reply_users'])) 
                    else:    reply_users.append(0)
                    if 'reply_count' in row.keys():
                        reply_count.append(row['reply_count'])
                        reply_users_count.append(row['reply_users_count'])
                        tm_thread_end.append(row['latest_reply'])
                    else:
                        reply_count.append(0)
                        reply_users_count.append(0)
                        tm_thread_end.append(row['ts'])
                except Exception as e:
                    print(e)

        data = zip(slack_id, student_id, week, msg_content, sender_id, time_msg, msg_dist, time_thread_st,
         reply_count, reply_users_count, reply_users, tm_thread_end)
        columns = ['slack_id', 'student_id', 'week', 'msg_content', 'sender_name', 'msg_sent_time', 'msg_dist_type',
         'time_thread_start', 'reply_count', 'reply_users_count', 'reply_users', 'tm_thread_end']
        # print("converting to dataframe")
        df = pd.DataFrame(data=data, columns=columns)
        dfall=dfall.append(df)
        dfall = dfall[dfall['sender_name'] != 'Not provided']

        dfall = dfall.reset_index(drop=True)

    dfall = dfall.merge(users, left_on='sender_name', right_on='id', how='inner')

    dfall = dfall.drop(['sender_name', 'id'], axis=1)

    print("converting from unix timestamp to good timestamp")


    dfall['time_thread_start'] = convert_2_timestamp('time_thread_start', dfall)
    dfall['msg_sent_time'] = convert_2_timestamp('msg_sent_time', dfall)
    dfall['tm_thread_end'] = convert_2_timestamp('tm_thread_end', dfall)
    dfall['channel'] = channel


    print(f"file returned successfully!!! {dfall.columns}")

    return dfall.to_csv(cfg.filename, index=False)
