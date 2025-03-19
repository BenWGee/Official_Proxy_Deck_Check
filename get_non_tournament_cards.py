import requests
import pandas as pd
import os

def get_cards_from_set(set_code):
    url = f"https://api.scryfall.com/cards/search"
    params = {
        'q': f'set:{set_code}',
        'order': 'name',
        'unique': 'prints'
    }

    cards = []  # Initialize an empty list to store card data

    while True:
        response = requests.get(url, params=params)

        if response.status_code != 200:
            print(f"Error fetching data: {response.status_code}")
            return pd.DataFrame()  # Return an empty DataFrame on error

        cards_data = response.json()
        cards.extend(cards_data.get('data', []))  # Add the current page of cards to the list

        # Check if there is a next page
        if 'next_page' in cards_data and cards_data['next_page']:
            # Update the URL to the next page
            url = cards_data['next_page']
        else:
            break  # Exit the loop if there are no more pages

    # Process the collected card data into a DataFrame
    card_info_list = []
    for card in cards:
        card_info = {
            'name': card.get('name'),
            'usd': card.get('prices', {}).get('usd'),
            'eur': card.get('prices', {}).get('eur'),
            'set': card.get('set')  # Add the set information
        }
        card_info_list.append(card_info)

    return pd.DataFrame(card_info_list)  # Return the list as a pandas DataFrame


def get_all_cards(set_codes):
    all_cards = pd.concat([get_cards_from_set(code) for code in set_codes], ignore_index=True)
    return all_cards

def parse_deck_file(deck_file):
    """Parse the deck file and return a list of card names."""
    _, file_extension = os.path.splitext(deck_file)

    card_names = []

    if file_extension.lower() == '.csv':
        # Read the CSV file
        deck_df = pd.read_csv(deck_file)
        card_names = deck_df['name'].tolist()
    elif file_extension.lower() == '.txt':
        # Read the TXT file
        with open(deck_file, 'r') as file:
            lines = file.readlines()

        for line in lines:
            line = line.strip()
            if line and not line.startswith('SIDEBOARD'):
                # Split the line to get the card name (ignore the count)
                card_name = ' '.join(line.split()[1:])  # Skip the first element (count)
                card_names.append(card_name)
    else:
        print("Unsupported file format. Please provide a .csv or .txt file.")

    return card_names

def add_tournament_proxy_versions(deck_file, all_cards, currency):
    # Parse the user's decklist from the file
    card_names = parse_deck_file(deck_file)

    # Create a new DataFrame from the card names
    deck = pd.DataFrame(card_names, columns=['name'])

    # Add available sets column
    deck['available sets'] = deck['name'].apply(
        lambda card_name: ', '.join(all_cards[all_cards['name'] == card_name]['set'].unique())
    )

    # Create a new DataFrame to hold the USD and EUR prices for each set
    for set_name in all_cards['set'].unique():
        # Filter cards for the current set
        set_cards = all_cards[all_cards['set'] == set_name]

        # Merge the prices into the deck DataFrame
        deck = deck.merge(set_cards[['name', currency]], on='name', how='left', suffixes=('', f'_{set_name}'))

        # Rename the columns to the desired format
        col_name = f'{set_name}_{currency}'
        deck.rename(columns={currency: col_name}, inplace=True)
        deck[col_name] = pd.to_numeric(deck[col_name], errors='coerce')


    return deck

def calculate_cheapest_prices(deck, currency):
    # Cols to add
    cash_cols = [col for col in deck.columns if col.endswith(f'_{currency}')]


    # Calculate the cheapest prices and corresponding sets
    deck['Cheapest_Price'] = deck[cash_cols].min(axis=1, numeric_only=True)
    deck['Cheapest_Set'] = deck.apply(
        lambda row: ', '.join([col[:-4] for col in cash_cols if row[col] == row['Cheapest_Price']]),
        axis=1
    )

    current_columns = list(deck.columns)

    # Rearranging the columns
    current_columns.remove('Cheapest_Price')
    current_columns.remove('Cheapest_Set')

    current_columns.insert(1, 'Cheapest_Price')
    current_columns.insert(2, 'Cheapest_Set')

    # Reorder the DataFrame
    deck = deck[current_columns]


    return deck

# Example usage
set_codes = ["WC97", "WC98", "WC99", "WC00", "WC01", "WC02", "WC03", "WC04", "30A", "CEI", "CED"]
all_cards = get_all_cards(set_codes)

# Assuming the decklist is in a file named 'deck.txt' or 'deck.csv'
deck_file = input("Deck name (txt or csv only): ")
currency = (input("Currency USD or EUR): ")).lower()

deck_with_versions = add_tournament_proxy_versions(deck_file, all_cards, currency)

# Calculate the cheapest prices and sets
deck_with_cheapest_prices = calculate_cheapest_prices(deck_with_versions, currency)

# Save the updated deck to a CSV file
output_file = 'deck_with_versions.csv'
deck_with_cheapest_prices.to_csv(output_file, index=False)

# Display a message indicating where the output was saved
print(f"Deck with tournament proxy versions saved to {output_file}.")
