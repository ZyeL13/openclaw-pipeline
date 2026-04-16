import requests, sys

API_KEY = "fEsZqG3sY8ZMVEBessv7ZU9e"  # daftar di remove.bg, gratis

def remove_bg(input_path, output_path):
    with open(input_path, 'rb') as f:
        response = requests.post(
            'https://api.remove.bg/v1.0/removebg',
            files={'image_file': f},
            data={'size': 'auto'},
            headers={'X-Api-Key': API_KEY},
        )
    if response.status_code == 200:
        with open(output_path, 'wb') as out:
            out.write(response.content)
        print(f"Saved: {output_path}")
    else:
        print(f"Error: {response.status_code}", response.text)

remove_bg(sys.argv[1], sys.argv[2])
