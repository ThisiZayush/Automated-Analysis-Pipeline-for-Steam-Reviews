import re
import pandas as pd
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

CLEAN_FILE = "Transformed_File.csv"
SCORED_FILE = "Sentiment_Score_File.csv"

# Keyword groups for aspect-based sentiment. Substring matching on purpose -
# "crash"/"crashes"/"crashing" and "bug"/"bugs"/"buggy" all match "crash"/"bug"
# without needing stemming. Tune these once you've seen what people actually
# talk about in the real data.
ASPECT_KEYWORDS = {
    "performance": ["bug", "crash", "glitch", "fps", "lag", "stutter", "freeze",
                    "optimi", "frame rate", "load time", "broken"],
    "story": ["story", "plot", "narrative", "character", "writing", "ending"],
    "gameplay": ["gameplay", "combat", "mechanic", "mission", "quest", "exploration"],
    "price": ["price", "worth", "expensive", "cheap", "value", "cost", "sale", "discount"],
    "graphics": ["graphics", "visual", "art style", "texture", "ray tracing"],
}


GAMING_SLANG_LEXICON = {
    "peak": 4.0,         # Maximum quality / The absolute best
    "cracked": 2.5,      # Extremely skilled or surprisingly good
    "goated": 3.4,       # Short for "Greatest of All Time"
    "fire": 2.5,         # Cool, amazing, or high quality
    "mid": -1.5,         # Mediocre, boring, or average (used as an insult)
    "cooked": -2.0,      # Ruined, failed, or completely broken
    "badass": 3.5,       # Cool, tough, or impressive
    "deal": 2.5,         # A good bargain or worth the money
    "insane": 4.0,       # Wildly good or mind-blowing
    "chumm": 3.5,        # Misspelling of a friendly term / buddy
    "insanely": 3.0,     # Extremely (boosts other positive words)
    "sick": 2.5,         # Cool or awesome (opposite of literal sickness)
    "crazy": 2.0,        # Wild or impressively chaotic
    "addicting": 3.0,    # So fun you can't stop playing
    "addictive": 3.0,    # Same as addicting
    "banger": 3.0,       # Something exceptionally good (often music or content)
    "masterpiece": 4.0,  # A flawless work of art
    "based": 2.5,        # Agreeable, authentic, or admirable
    "kino": 3.0,         # Cinema-quality / high-art storytelling
    "slaps": 2.5,        # Is exceptionally good
    "pog": 2.5,          # Exciting or cool (gaming streaming slang)
    "poggers": 2.5,      # Same as pog
    "gigachad": 3.0,     # An ultimate, highly praised legend or alpha figure
    "hiddengem": 3.5,    # An underrated masterpiece people missed out on
    "dogwater": -3.0,    # Utterly terrible / Garbage quality
    "dogshit": -3.5,     # Extremely vulgar way to say terrible
    "trash": -3.0,       # Worthless or very bad
    "garbage": -3.0,     # Same as trash
    "scam": -3.5,        # A rip-off or deceptive product
    "abandonware": -3.0, # A game that the creators stopped supporting/fixing
    "cashgrab": -3.5,    # Made purely to steal people's money without effort
    "cope": -2.0,        # Delusional denial (mocking players who defend a bad game)
    "seethe": -2.0,      # Being angrily upset about something
    "preem": 3.5,        # Cyberpunk slang for "premium" / Excellent
    "nova": 3.0,         # Cyberpunk slang for cool or awesome
    "choom": 2.0,        # Cyberpunk slang for a friend or buddy ("Buy it, friend")
    "choomba": 2.0,      # Same as choom (friend)
    "shimra": 2.5,       # Cyberpunk slang meaning awesome
    "gonk": -2.5,        # Cyberpunk slang for an idiot or fool
    "corpo": -2.0,       # Cyberpunk slang for a greedy corporation (used negatively toward the publisher)
    "eddies": 0.0,       # Cyberpunk slang for in-game money (neutral on its own)
    "klep": -1.0,        # Cyberpunk slang for stealing
    "scop": -3.0,        # Cyberpunk slang for low-quality fake food (used to mean trash)
    "scopshit": -3.5,    # Extreme version of scop (completely garbage)
    "keanu": 3.0,            # Refers to actor Keanu Reeves (plays Johnny Silverhand)
    "idris": 3.0,            # Refers to actor Idris Elba (plays Solomon Reed)
    "elba": 3.0,             # Refers to actor Idris Elba
    "johnny": 2.5,           # Refers to Johnny Silverhand (the main companion character)
    "silverhand": 2.5,       # Johnny's last name, heavily praised in reviews
    "reed": 2.5,             # Refers to Solomon Reed (from the expansion)

    # Open World & Setting
    "nightcity": 2.5,        # The massive, detailed open-world city where the game takes place
    "breathtaking": 3.5,     # A iconic phrase heavily associated with Keanu Reeves' game reveal
    "tpose": -2.5,           # A famous glitch where characters freeze in a cross-like shape
    "openworld": 2.0,        # Describes the freedom to explore the massive map
    
    # Story-Rich & Cinematic Elements
    "cinematic": 3.0,        # Movie-like quality, used to praise the story presentation
    "immersive": 2.5,        # Making the player feel genuinely trapped inside the game's world
    "branching": 2.0,        # Story choices that change how the game ends
    "emotional": 2.5,        # A story that makes players feel strong emotions (sadness, joy)
    "atmospheric": 2.5,      # Having a strong, mood-setting vibe (visuals + music + story)

    # Key Expansions & Media Boosts
    "phantomliberty": 3.5,   # The critically acclaimed story expansion pack
    "edgerunners": 3.5,      # The hit Netflix anime series that massively revived the game's reputation
}
 
 
def ensure_vader_lexicon():
    # VADER's word-score dictionary is downloaded once and cached locally after that
    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        nltk.download("vader_lexicon")
 
 
def get_analyzer():
    # lexicon.update() only patches this in-memory copy of the dictionary -
    # it doesn't touch the downloaded file, so this has to run every time
    # an analyzer is built rather than being a one-off setup step.
    analyzer = SentimentIntensityAnalyzer()
    analyzer.lexicon.update(GAMING_SLANG_LEXICON)
    return analyzer


def label_from_compound(compound_score):
    # These thresholds are VADER's own documented convention, not an arbitrary choice
    if compound_score >= 0.05:
        return "positive"
    elif compound_score <= -0.05:
        return "negative"
    else:
        return "neutral"

def split_sentences(text):
    # Simple sentence splitter - good enough for keyword matching without an
    # extra nltk download for a proper sentence tokenizer.
    return re.split(r"(?<=[.!?])\s+", text)


def aspect_sentiment(text, analyzer):
    sentences = split_sentences(text)
    lower_sentences = [s.lower() for s in sentences]

    result = {}

    for aspect, keywords in ASPECT_KEYWORDS.items():
        matching = []

        # Loop through sentences and lowercase sentences side-by-side
        for s,s_lower in zip(sentences, lower_sentences):

            # Check if any keyword is inside this specific sentence
            found_keyword = False

            for kw in keywords:
                if kw in s_lower:
                    found_keyword = True
                    break       # Stop searching once we find a match

            # If a keyword was found, save the original sentence
            if found_keyword:
                matching.append(s)

        # Score the aspect based on the sentences we found
        if matching:
            combined = " ".join(matching)
            result[f"mentions_{aspect}"] = True
            result[f"{aspect}_sentiment"] = analyzer.polarity_scores(combined)["compound"]
        else:
            result[f"mentions_{aspect}"] = False
            result[f"{aspect}_sentiment"] = None

    return result


def score_sentiment(df):
    analyzer = get_analyzer()

    # Overall review sentiment
    overall_scores = df["review_text"].astype(str).apply(analyzer.polarity_scores)
    overall_df = pd.DataFrame(list(overall_scores))
    df["sentiment_neg"] = overall_df["neg"]
    df["sentiment_neu"] = overall_df["neu"]
    df["sentiment_pos"] = overall_df["pos"]
    df["sentiment_compound"] = overall_df["compound"]
    df["sentiment_label"] = df["sentiment_compound"].apply(label_from_compound)

    # Aspect-based sentiment: what specifically is being praised or criticized
    aspect_results = df["review_text"].astype(str).apply(lambda t: aspect_sentiment(t, analyzer))
    aspect_df = pd.DataFrame(list(aspect_results))
    df = pd.concat([df.reset_index(drop=True), aspect_df.reset_index(drop=True)], axis=1)

    return df


def main():
    print(f"Loading cleaned reviews from {CLEAN_FILE}...")
    df = pd.read_csv(CLEAN_FILE)
    print(f"Loaded {len(df)} reviews")

    ensure_vader_lexicon()

    print("Scoring overall + aspect-based sentiment with VADER...")
    df = score_sentiment(df)

    df.to_csv(SCORED_FILE, index=False)
    print(f"Saved scored data to {SCORED_FILE}")

    print("\n--- Overall Sentiment Summary ---")
    print(df["sentiment_label"].value_counts())
    print(f"Average compound score: {df['sentiment_compound'].mean():.3f}")

    # Sanity check: does VADER's read on the text roughly agree with the reviewer's
    # own thumbs up/down? High agreement = the pipeline is behaving sensibly.
    # Disagreement cases are actually interesting - e.g. a measured, calmly-written
    # complaint that still ends in "not recommended".
    agrees = (
        ((df["sentiment_label"] == "positive") & (df["voted_up"] == True)) |
        ((df["sentiment_label"] == "negative") & (df["voted_up"] == False))
    )
    print(f"Agreement with Steam's own voted_up flag: {agrees.mean()*100:.1f}%")

    print("\n--- Aspect Mentions & Average Sentiment ---")
    for aspect in ASPECT_KEYWORDS:
        mentioned = df[df[f"mentions_{aspect}"] == True]
        if len(mentioned) > 0:
            avg = mentioned[f"{aspect}_sentiment"].mean()
            print(f"{aspect:12s}: mentioned in {len(mentioned):6d} reviews, avg sentiment {avg:+.3f}")
        else:
            print(f"{aspect:12s}: not mentioned in any review")


if __name__ == "__main__":
    main()
    