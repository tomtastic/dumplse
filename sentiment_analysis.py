#!/usr/bin/env python3
"""A rudimentary sentiment analysis tool for examining the default sqlite db
produced by dumplse.py"""
import re
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict

# Sentiment keyword sets
POSITIVE = {
        'should accumulate', 'will accumlate', 'im accumulating', 'i adore',
        'advise buying', 'this is affordable', 'attractive', 'awesome',
        'bargain', 'beating', 'big upside', 'big news just', 'i bought', 'will bounce',
        'bouncing', 'breaking out', 'breakthrough', 'bull', 'bullish',
        'buy now', 'buying', 'is cheap', 'will climb', 'climbing', 'confident',
        'discount', 'discounted', 'encouraged', 'endorse', 'exceed',
        'exceeded', 'exceeding', 'excellent results',
        'exceptional', 'fabulous', 'fantastic', 'favor', 'going up', 'golden',
        'goldmine', 'good buy', 'good gains', 'good investment', 'good news',
        'good potential', 'good profit', 'good upside', 'good value',
        'great buy', 'great company', 'great news', 'great value',
        'has upside', 'high potential', 'increased my holding', 'jackpot',
        'loaded', 'loading', 'load up', 'looking forward', 'looking good', 'magnificent',
        'marvelous', 'massive upside', 'moon', 'mooning', 'moving up',
        'nice profit', 'opportunity', 'optimistic', 'outperform',
        'outperformed', 'outperforming', 'outstanding', 'perfect',
        'phenomenal', 'positive', 'positive news', 'make profit',
        'promising', 'purchased', 'purchasing', 'rallied', 'rally', 'rallying',
        'really like', 're-rating soon', 'rebound', 'rebounding', 'recommend', 'will recover',
        'is recovering', 'rise to', 'rise from', 'rising', 'robust', 'rocket', 'rocketing',
        'should buy', 'will soar', 'soaring', 'steal', 'strong',
        'be successful', 'superb', 'support', 'surge', 'surging', 'terrific',
        'thrilled', 'time to buy', 'top', 'topped', 'topping', 'underpriced',
        'undervalued', 'upbeat', 'very good', 'very positive',
        'will break out', 'will buy', 'will go up', 'will move up',
        'will rally', 'will soar', 'winner'
        }

NEGATIVE = {
        'abysmal', 'alert', 'anxious', 'appalling', 'atrocious', 'avoid',
        'awful', 'bad feeling', 'bearish', 'beware', 'big drop', 'big loss', 'bleak',
        'blood bath', 'bloodbath', 'bubble', 'careful', 'carnage',
        'catastrophe', 'catastrophic', 'caution', 'collapse', 'collapsing',
        'concern', 'concerned', 'crash', 'crashing', 'danger', 'dangerous',
        'dead money', 'decline', 'declining', 'destruction', 'devastating',
        'dire', 'disappointing results', 'disaster', 'disastrous',
        'dive', 'diving', 'dont like', 'down from here',
        'downside', 'dreadful', 'will drop', 'dropping', 'dump', 'dumped',
        'dumping', 'exit', 'exited', 'exiting', 'expensive', 'failing',
        'failure', 'fall', 'falling', 'fearful', 'fragile', 'frothy', 
        'going down', 'going nowhere', 'grim', 'heavy loss', 'inflated',
        'liquidate', 'liquidated', 'liquidating', 'lose', 'a loser', 'losing',
        'loss', 'losses', 'manipulated', 'manipulation', 'massacre',
        'moving down', 'negative', 'nervous', 'nightmare', 'off the table',
        'overpriced', 'overvalued', 'pessimistic', 'plunge', 'plunging',
        'poor performance', 'poor results', 'precarious', 'pricey', 'promising to go',
        'pump and dump', 'not recommend', 'red', 'refuse', 'reject', 'too rich', 'risky',
        'ruin', 'scam', 'scared', 'will sell', 'selling', 'shaky',
        'should sell', 'slide', 'sliding', 'sold', 'stay away', 'take a hit',
        'take the hit', 'tank', 'tanking', 'terrible news', 'threat',
        'time to sell', 'toxic', 'bear trap', 'trouble', 'tumble', 'tumbling',
        'unload', 'unloaded', 'unloading', 'unstable', 'vulnerable',
        'warning', 'waste of', 'watch out', 'weak', 'worried', 'worry',
        'worthless', 'wreck', 'wrecked'
        }


def highlight_words(text, word_list, highlight_format="**{}**"):
    """Highlight words in text that match those in word_list"""
    pattern = r'\b(' + '|'.join(re.escape(word) for word in word_list) + r')\b'
    return re.sub(pattern, lambda m: highlight_format.format(m.group(1)), text, flags=re.IGNORECASE)


def analyze_sentiment_predictions(db_path='posts.sqlite3', start_date='2024-01', end_date=None, ticker=None, username=None, threshold_pct=0.2, day_range='3-14'):
    """Analyze sentiment prediction accuracy for an n-day timeframe"""

    # Parse day range
    start_day, end_day = map(int, day_range.split('-'))

    # Default to current date if end_date not provided
    if end_date is None:
        today = datetime.now()
        end_date = f'{today.year}-{today.month:02d}'

    # Parse start and end dates
    start_year, start_month = map(int, start_date.split('-'))
    end_year, end_month = map(int, end_date.split('-'))

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    #if POSITIVE & NEGATIVE == set():
    #    print(f"Error in sets, duplicate sentiments: {POSITIVE & NEGATIVE}\n")
    #    sys.exit(1)

    # Build dynamic SQL query using sentiment sets with word boundaries
    def make_word_boundary_condition(term):
        escaped = term.replace("'", "''")  # Escape single quotes for SQL
        return f"(LOWER(text) LIKE '% {escaped.lower()} %' OR LOWER(text) LIKE '{escaped.lower()} %' OR LOWER(text) LIKE '% {escaped.lower()}' OR LOWER(text) = '{escaped.lower()}')"
    
    positive_conditions = " OR ".join([make_word_boundary_condition(term) for term in POSITIVE])
    negative_conditions = " OR ".join([make_word_boundary_condition(term) for term in NEGATIVE])

    predictions_query = f"""
    SELECT 
        username,
        atprice as pred_price,
        date as pred_date,
        CASE 
            WHEN ({positive_conditions}) AND NOT ({negative_conditions}) THEN 'BULLISH'
            WHEN ({negative_conditions}) AND NOT ({positive_conditions}) THEN 'BEARISH'
            ELSE NULL
        END as sentiment,
        text as text_sample,
        ticker as ticker
    FROM posts 
    WHERE date >= ? AND date <= ?
    AND (({positive_conditions}) OR ({negative_conditions}))
    {' AND ticker = ?' if ticker else ''}
    {' AND username = ?' if username else ''}
    """

    params = [f'{start_year}-{start_month:02d}-01', f'{end_year}-{end_month:02d}-31']
    if ticker:
        params.append(ticker)
    if username:
        params.append(username)

    cursor.execute(predictions_query, params)
    predictions = cursor.fetchall()

    # Get all price data
    cursor.execute("SELECT date, atprice, ticker FROM posts WHERE atprice IS NOT NULL ORDER BY date")
    price_data = cursor.fetchall()

    conn.close()

    # Convert to dict for faster lookup - key by (date, ticker)
    prices = {}
    for date_str, price, ticker_name in price_data:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        prices[(date_obj.date(), ticker_name)] = price

    results = []

    for username, pred_price, pred_date_str, sentiment, text_sample, ticker in predictions:
        if not sentiment:
            continue

        pred_date = datetime.strptime(pred_date_str, '%Y-%m-%d %H:%M:%S').date()

        # Find future prices of the ticker within n days after prediction
        future_prices = []
        threshold_date = None
        for i in range(start_day, end_day + 1):
            future_date = pred_date + timedelta(days=i)
            if (future_date, ticker) in prices:
                price = float(prices[(future_date, ticker)])
                future_prices.append(price)
                # Check if threshold met on this date
                if not threshold_date:
                    if sentiment == 'BULLISH' and price > float(pred_price) * (1 + threshold_pct):
                        threshold_date = future_date
                    elif sentiment == 'BEARISH' and price < float(pred_price) * (1 - threshold_pct):
                        threshold_date = future_date

        if len(future_prices) >= 3:  # Want at least 3 predictions to make a good average
            # Convert to float and filter out None values
            valid_prices = [float(p) for p in future_prices if p is not None]
            if len(valid_prices) >= 3:
                avg_future_price = sum(valid_prices) / len(valid_prices)
            price_change_pct = (avg_future_price - float(pred_price)) / float(pred_price) * 100

            # Determine if prediction was correct (% threshold)
            correct = False
            if sentiment == 'BULLISH' and avg_future_price > float(pred_price) * (1 + threshold_pct):
                correct = True
            elif sentiment == 'BEARISH' and avg_future_price < float(pred_price) * (1 - threshold_pct):
                correct = True

            results.append({
                'username': username,
                'pred_price': float(pred_price),
                'pred_date': pred_date,
                'sentiment': sentiment,
                'avg_future_price': avg_future_price,
                'price_change_pct': price_change_pct,
                'correct': correct,
                'ticker': ticker,
                'text_sample': text_sample,
                'threshold_date': threshold_date
            })

    # Calculate accuracy by user
    user_stats = defaultdict(lambda: {'total': 0, 'correct': 0, 'price_moves': []})

    for result in results:
        username = result['username']
        user_stats[username]['total'] += 1
        if result['correct']:
            user_stats[username]['correct'] += 1
        user_stats[username]['price_moves'].append(abs(result['price_change_pct']))

    # Filter users with at least 3 predictions and calculate final stats
    accuracy_stats = {}
    for username, stats in user_stats.items():
        if stats['total'] >= 3:
            accuracy_pct = (stats['correct'] / stats['total']) * 100
            avg_price_move = sum(stats['price_moves']) / len(stats['price_moves'])
            accuracy_stats[username] = {
                'total_predictions': stats['total'],
                'correct_calls': stats['correct'],
                'accuracy_pct': accuracy_pct,
                'avg_price_move': avg_price_move
            }

    # Sort by accuracy, then by total predictions
    sorted_users = sorted(accuracy_stats.items(), 
                         key=lambda x: (x[1]['accuracy_pct'], x[1]['total_predictions']), 
                         reverse=True)

    return sorted_users, results

def get_top_predictions(results, username, n):
    """Get top predictions for a specific user"""
    user_results = [r for r in results if r['username'] == username]
    user_results.sort(key=lambda x: abs(x['price_change_pct']), reverse=True)
    n = len(user_results) if len(user_results) <= int(n) else int(n)
    return user_results[:n]

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze sentiment prediction accuracy')
    parser.add_argument('--ticker', '-t', help='Filter by ticker symbol')
    parser.add_argument('--username', '-u', help='Filter by username')
    parser.add_argument('--percent', '-p', type=float, default=0.2, help='Price threshold percentage (default: 0.2 = 20%%)')
    parser.add_argument('--start-date', '-s', default='2024-01', help='Start date in YYYY-MM format (default: 2024-01)')
    parser.add_argument('--end-date', '-e', help='End date in YYYY-MM format (default: current month)')
    parser.add_argument('--future', '-f', default='3-14', help='Future price prediction day range (default: 3-14)')
    parser.add_argument('--number', '-n', default='3', help='Number of top predictions returned(default: 3)')
    args = parser.parse_args()
    
    ticker_msg = f" for {args.ticker}" if args.ticker else ""
    username_msg = f" by {args.username}" if args.username else ""
    print(f"Analyzing price prediction accuracy (+/-{round(args.percent*100)}% within {args.future} days) ({args.start_date} to {args.end_date or 'current'}){ticker_msg}{username_msg}...")

    accuracy_stats, results = analyze_sentiment_predictions(ticker=args.ticker.upper(), username=args.username, threshold_pct=args.percent, start_date=args.start_date, end_date=args.end_date, day_range=args.future)

    print("\nTop 20 Most Accurate Predictors:")
    print("=" * 80)
    print(f"{'Username':<20} {'Predictions':<12} {'Correct':<8} {'Accuracy %':<10} {'Avg Move %':<10}")
    print("-" * 80)

    for username, stats in accuracy_stats[:20]:
        print(f"{username:<20} {stats['total_predictions']:<12} {stats['correct_calls']:<8} "
              f"{stats['accuracy_pct']:<10.1f} {stats['avg_price_move']:<10.1f}")

    # Show examples from top n performers
    n = 3
    top_n_users = [username for username, _ in accuracy_stats[:n]]

    for user in top_n_users:
        user_found = False
        for username, _ in accuracy_stats:
            if username == user:
                user_found = True
                break

        if user_found:
            print(f"\n\nTop predictions from {user}:")
            print("=" * 60)
            examples = get_top_predictions(results, user, args.number)
            highlight_bull = "\033[32m\033[7m{}\033[0m" # Green
            highlight_bear = "\033[31m\033[7m{}\033[0m" # Red
            for pred in examples:
                status = "\33[32m✓" if pred['correct'] else "\33[31m✗"

                if 'BULLISH' in pred['sentiment']:
                    threshold_info = f" (hit {pred['threshold_date']})" if pred['threshold_date'] else ""
                    print(f"{status} {pred['ticker']} {pred['pred_date']} | "
                          f"{pred['sentiment']} @ {pred['pred_price']:.2f}p → "
                          f"{pred['avg_future_price']:.2f}p ({pred['price_change_pct']:+.1f}%){threshold_info}\33[0m")
                    print(f"   {highlight_words(pred['text_sample'], POSITIVE, highlight_bull)}")

                if 'BEARISH' in pred['sentiment']:
                    threshold_info = f" (hit {pred['threshold_date']})" if pred['threshold_date'] else ""
                    print(f"{status} {pred['ticker']} {pred['pred_date']} | "
                          f"{pred['sentiment']} @ {pred['pred_price']:.2f}p → "
                          f"{pred['avg_future_price']:.2f}p ({pred['price_change_pct']:+.1f}%){threshold_info}\33[0m")
                    print(f"   {highlight_words(pred['text_sample'], NEGATIVE, highlight_bear)}")

                print()
