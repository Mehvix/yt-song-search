import argparse
import os
import re

from googleapiclient.discovery import build

END_OF_PAGE = "%%EOP%%"

def extract_video_id(url):
    pattern = r"(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([^?&\/]+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        return None


def check_song_string(string):
    pattern = r"song\?*"
    return bool(re.search(pattern, string, re.IGNORECASE))


class SongSearch:
    def __init__(self, video_url: str, API_key: str = None) -> None:
        # ===================== Set API key below ===================== #
        self.API_key = os.environ.get("YT_API") or API_key or "__API_KEY__"
        # or as env variable i.e. `export YT_API="__API_KEY__"`         #
        # ============================================================= #
        self.youtube = build("youtube", "v3", developerKey=self.API_key)
        self.video_id = extract_video_id(video_url)

    def fetch_comment(self, comment_type: str, id: str, next_token: str = None) -> dict:
        if next_token is END_OF_PAGE:
            return None

        assert comment_type in ["video", "comment"]

        params = {
            "textFormat": "plainText",
            "maxResults": 100,
        }

        if next_token is not None:
            params["pageToken"] = next_token

        part = "snippet"
        if comment_type == "video":
            part += ",replies"
            params["videoId"] = id
            params["order"] = "relevance"   # is this ~ likes?
        elif comment_type == "comment":
            params["parentId"] = id

        if comment_type == "video":
            return self.youtube.commentThreads().list(part=part, **params).execute()
        elif comment_type == "comment":
            return self.youtube.comments().list(part=part, **params).execute()




    def get_song_comments(self) -> dict:
        response = self.fetch_comment("video", self.video_id)

        comments = dict()
        while response:
            for item in response["items"]:
                comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                if not check_song_string(comment):  # skip if not
                    continue

                if (
                    "totalReplyCount" not in item["snippet"]
                    or item["snippet"]["totalReplyCount"] == 0
                ):  # skip if no replies
                    continue

                comments[comment] = self.get_comment_replies(
                    item["snippet"]["topLevelComment"]["id"]
                )

            response = self.fetch_comment(
                "video", self.video_id, response.get("nextPageToken", END_OF_PAGE)
            )

        return comments

    def get_comment_replies(self, head_id: str) -> list:
        response = self.fetch_comment("comment", head_id)

        comments = []
        while response:
            for item in response["items"]:
                comments.append(item["snippet"]["textDisplay"])

            response = self.fetch_comment(
                "comment", head_id, response.get("nextPageToken", END_OF_PAGE)
            )

        return comments


def main():
    parser = argparse.ArgumentParser(description="YouTube Comment Song Search")
    parser.add_argument("video_url", help="YouTube video URL")

    args = parser.parse_args()

    song_search = SongSearch(args.video_url)
    comments = song_search.get_song_comments()
    # print(comments)

    for comment, replies in comments.items():
        print("========================================")
        print("+ " + comment)
        print('\n'.join([f'=> {r}' for r in replies]))


if __name__ == "__main__":
    main()
