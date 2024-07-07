import subprocess
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def create_github_repo(username, token, repo_name):
    url = "https://api.github.com/user/repos"
    payload = {
        "name": repo_name,
        "private": True
    }
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 201:
        print(f"Repository '{repo_name}' created successfully.")
        return response.json()["clone_url"]
    else:
        print(f"Failed to create repository: {response.json()}")
        return None

def init_local_repo(repo_name):
    if not os.path.exists(repo_name):
        os.makedirs(repo_name)
        subprocess.run(["git", "init"], cwd=repo_name)
        print(f"Initialized empty Git repository in {os.path.abspath(repo_name)}/.git/")
    else:
        print(f"Directory '{repo_name}' already exists.")

def add_files_to_repo(repo_name):
    with open(os.path.join(repo_name, "README.md"), "w") as f:
        f.write(f"# {repo_name}\n")

    subprocess.run(["git", "add", "."], cwd=repo_name)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_name)
    print("Added README.md and committed initial commit.")

def push_to_github(repo_name, repo_url, username, token):
    # Construct the HTTPS URL with token
    token_url = repo_url.replace("https://", f"https://{username}:{token}@")
    subprocess.run(["git", "remote", "add", "origin", token_url], cwd=repo_name)
    subprocess.run(["git", "branch", "-M", "main"], cwd=repo_name)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=repo_name)
    print(f"Pushed local repository '{repo_name}' to GitHub.")

def main():
    username = os.getenv("GITHUB_USERNAME")
    token = os.getenv("GITHUB_TOKEN")
    repo_name = input("Repository Name: ")

    repo_url = create_github_repo(username, token, repo_name)
    if repo_url:
        init_local_repo(repo_name)
        add_files_to_repo(repo_name)
        push_to_github(repo_name, repo_url, username, token)
    else:
        print("Failed to create and push repository.")

if __name__ == "__main__":
    main()
