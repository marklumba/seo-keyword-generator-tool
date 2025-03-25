import customtkinter as ctk
import threading
import random
import json
import os
import requests
from datetime import datetime
from tkinter import messagebox
from pytrends.request import TrendReq

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class KeywordDataSource:
    def get_keyword_data(self, keyword, **kwargs):
        raise NotImplementedError
    def get_related_keywords(self, keyword, **kwargs):
        raise NotImplementedError

class GoogleTrendsDataSource(KeywordDataSource):
    def __init__(self):
        self.pytrends = TrendReq(hl='en-US', tz=120)

    def get_related_keywords(self, keyword, limit=20, **kwargs):
        try:
            self.pytrends.build_payload([keyword], timeframe='today 12-m', geo='US')
            related = self.pytrends.related_queries()
            if not related or keyword not in related:
                return []
            top = related[keyword]['top'][:limit // 2].to_dict('records')
            rising = related[keyword]['rising'][:limit // 2].to_dict('records')
            return [{'keyword': r['query'], 'score': r['value'], 'type': 'top' if i < limit // 2 else 'rising'}
                    for i, r in enumerate(top + rising)]
        except Exception as e:
            print(f"Google Trends error: {e}")
            return []

    def get_keyword_data(self, keyword, **kwargs):
        try:
            self.pytrends.build_payload([keyword], timeframe='today 12-m', geo='US')
            interest = self.pytrends.interest_over_time()
            return {'keyword': keyword, 'interest': interest[keyword].mean() if keyword in interest else 0}
        except Exception as e:
            print(f"Google Trends data error: {e}")
            return {'keyword': keyword, 'interest': 0}

class SerpApiDataSource(KeywordDataSource):
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search.json" 

    def get_related_keywords(self, keyword, limit=8, **kwargs):
        if not self.api_key:
            return self._get_mock_related_keywords(keyword, limit)
        params = {'q': keyword, 'gl': 'us', 'hl': 'en', 'api_key': self.api_key}
        response = requests.get(self.base_url, params=params)
        related_keywords = []
        if response.status_code == 200:
            data = response.json()
            if 'related_searches' in data:
                for item in data['related_searches'][:limit]:
                    related_keywords.append({'keyword': item['query'], 'score': random.randint(50, 100), 'type': 'related'})
            if 'related_questions' in data:
                for item in data['related_questions'][:limit]:
                    related_keywords.append({'keyword': item['question'], 'score': random.randint(50, 100), 'type': 'question'})
        return related_keywords if related_keywords else self._get_mock_related_keywords(keyword, limit)

    def get_keyword_data(self, keyword, **kwargs):
        if not self.api_key:
            return self._get_mock_keyword_data(keyword)
        params = {'q': keyword, 'gl': 'us', 'hl': 'en', 'api_key': self.api_key}
        response = requests.get(self.base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            return {
                'keyword': keyword,
                'total_results': data.get('search_information', {}).get('total_results', 'N/A'),
                'time_taken': data.get('search_metadata', {}).get('processing_time_ms', 0) / 1000
            }
        return self._get_mock_keyword_data(keyword)

    def _get_mock_related_keywords(self, keyword, limit=8):
        base_keywords = [f"best {keyword}", f"{keyword} tutorial", f"how to use {keyword}", f"{keyword} examples"]
        return [{'keyword': kw, 'score': random.randint(50, 100), 'type': 'related'} for kw in random.sample(base_keywords, min(limit, len(base_keywords)))]

    def _get_mock_keyword_data(self, keyword):
        return {'keyword': keyword, 'total_results': f"{random.randint(1, 9)},{random.randint(100, 999)}", 'time_taken': random.uniform(0.1, 0.9)}


class KeywordGenerator:
    def __init__(self, data_sources=None):
        self.data_sources = data_sources or []
        self.prefixes = ["best", "top", "how to", "cheap", "free", "new", "ultimate", "most popular", "trending", "affordable", 
                         "premium", "essential", "recommended", "value", "reliable", "must-have", "exclusive", "diy", "innovative",
                         "advanced", "proven", "favorite", "professional", "beginner-friendly", "expert-level", "revolutionary", 
                         "limited-edition"]
        self.suffixes = ["guide", "tips", "reviews", "for beginners", "tutorial", "trends",
                         "insights", "recommendations", "expert advice", "strategies", 
                         "case studies", "step-by-step instructions", "how-to guides", 
                         "best practices", "in-depth analysis", "FAQs", "user stories", 
                         "latest updates", "predictions"]

        self.question_starters = ["how", "what", "why", "where", "when", "who","which", "whom", "whose", "can", "should", "could",
                                  "would", "is", "are", "did", "does", "will", "may", "might", "shall"]


    def add_custom_pattern(self, prefixes=None, suffixes=None, questions=None):
        if prefixes:
            self.prefixes.extend(prefixes)
        if suffixes:
            self.suffixes.extend(suffixes)
        if questions:
            self.question_starters.extend(questions)

    def generate_keywords(self, seed_keyword, count=10, include_prefixes=True, include_suffixes=True, include_questions=True, include_api_data=True):
        if not seed_keyword.strip():
            return []
        keywords = [seed_keyword.strip().lower()]
        seed = keywords[0]
        if include_api_data and self.data_sources:
            related_keywords = self.get_related_keywords(seed, limit=count // 2)
            keywords.extend(item['keyword'] for item in related_keywords)
        if include_prefixes:
            keywords.extend(f"{prefix} {seed}" for prefix in random.sample(self.prefixes, min(len(self.prefixes), count // 4)))
        if include_suffixes:
            keywords.extend(f"{seed} {suffix}" for suffix in random.sample(self.suffixes, min(len(self.suffixes), count // 4)))
        if include_questions:
            keywords.extend(f"{starter} {seed}" for starter in random.sample(self.question_starters, min(len(self.question_starters), count // 4)))
        return list(dict.fromkeys(keywords))[:count]

    def get_related_keywords(self, seed_keyword, limit=10):
        all_related = []
        for source in self.data_sources:
            try:
                related = source.get_related_keywords(seed_keyword, limit=limit)
                all_related.extend(related)
                if len(all_related) >= limit:
                    break
            except Exception as e:
                print(f"Error fetching related keywords: {e}")
        unique_keywords = {item['keyword']: item for item in all_related}
        return list(unique_keywords.values())[:limit]

    def get_keyword_data(self, keyword):
        for source in self.data_sources:
            try:
                return source.get_keyword_data(keyword)
            except Exception as e:
                print(f"Error fetching keyword data: {e}")
        return {'keyword': keyword}

    def filter_keywords(self, keywords, min_length=5):
        return [kw for kw in keywords if len(kw) >= min_length]


class SEOKeywordGeneratorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.setup_data_sources()
        self.generator = KeywordGenerator(data_sources=[self.google_trends_source, self.serpapi_source])
        self.title("SEO Keyword Generator")
        self.geometry("900x700")
        self.minsize(700, 600)
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.title_label = ctk.CTkLabel(self.main_frame, text="SEO Keyword Generator", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(pady=(0, 20))
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        self.tabview.add("Generator")
        self.tabview.add("API Settings")
        self.setup_generator_tab()
        self.setup_api_settings_tab()
        self.status_var = ctk.StringVar(value="Ready")
        self.status_bar = ctk.CTkLabel(self, textvariable=self.status_var, height=25)
        self.status_bar.pack(fill="x", side="bottom", padx=10, pady=5)
        self.load_api_keys()

    def setup_data_sources(self):
        self.google_trends_source = GoogleTrendsDataSource()
        self.serpapi_source = SerpApiDataSource()
        #self.serpapi_source = SerpApiDataSource(api_key="856c1e32c63ccc796115ca4a7c82c94b2b754d7620eef320fcc5098993447835")  # Replace with your actual key

    def setup_generator_tab(self):
        tab = self.tabview.tab("Generator")
        self.input_frame = ctk.CTkFrame(tab)
        self.input_frame.pack(fill="x", padx=10, pady=10)
        self.keyword_label = ctk.CTkLabel(self.input_frame, text="Seed Keyword:")
        self.keyword_label.grid(row=0, column=0, padx=10, pady=10)
        self.keyword_entry = ctk.CTkEntry(self.input_frame, width=300)
        self.keyword_entry.grid(row=0, column=1, padx=10, pady=10)
        self.count_var = ctk.IntVar(value=20)
        self.count_slider = ctk.CTkSlider(self.input_frame, from_=5, to=50, number_of_steps=9, variable=self.count_var, width=300)
        self.count_slider.grid(row=1, column=1, padx=10, pady=10)
        self.options_frame = ctk.CTkFrame(tab)
        self.options_frame.pack(fill="x", padx=10, pady=10)
        self.include_prefixes_var = ctk.BooleanVar(value=True)
        self.include_prefixes = ctk.CTkCheckBox(self.options_frame, text="Prefixes", variable=self.include_prefixes_var)
        self.include_prefixes.grid(row=0, column=0, padx=20, pady=10)
        self.include_suffixes_var = ctk.BooleanVar(value=True)
        self.include_suffixes = ctk.CTkCheckBox(self.options_frame, text="Suffixes", variable=self.include_suffixes_var)
        self.include_suffixes.grid(row=0, column=1, padx=20, pady=10)
        self.include_questions_var = ctk.BooleanVar(value=True)
        self.include_questions = ctk.CTkCheckBox(self.options_frame, text="Questions", variable=self.include_questions_var)
        self.include_questions.grid(row=0, column=2, padx=20, pady=10)
        self.include_api_data_var = ctk.BooleanVar(value=True)
        self.include_api_data = ctk.CTkCheckBox(self.options_frame, text="API Data", variable=self.include_api_data_var)
        self.include_api_data.grid(row=0, column=3, padx=20, pady=10)
        self.generate_button = ctk.CTkButton(tab, text="Generate", command=self.generate_keywords, height=40)
        self.generate_button.pack(pady=20)
        self.progress_var = ctk.DoubleVar(value=0)
        self.progress = ctk.CTkProgressBar(tab, variable=self.progress_var)
        self.progress.pack(fill="x", padx=20, pady=(0, 10))
        self.results_text = ctk.CTkTextbox(tab, height=200)
        self.results_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.copy_button = ctk.CTkButton(tab, text="Copy", command=self.copy_to_clipboard)
        self.copy_button.pack(side="left", padx=10, pady=10)
        self.save_button = ctk.CTkButton(tab, text="Save", command=self.save_to_file)
        self.save_button.pack(side="left", padx=10, pady=10)

    def setup_api_settings_tab(self):
        tab = self.tabview.tab("API Settings")
        self.serpapi_key_var = ctk.StringVar(value="")
        self.serpapi_key_entry = ctk.CTkEntry(tab, width=400, textvariable=self.serpapi_key_var, show="•")
        self.serpapi_key_entry.pack(pady=10)
        self.serpapi_show_var = ctk.BooleanVar(value=False)
        self.serpapi_show_key = ctk.CTkCheckBox(tab, text="Show Key", variable=self.serpapi_show_var, command=self.toggle_show_serpapi_key)
        self.serpapi_show_key.pack(pady=5)
        self.save_settings_button = ctk.CTkButton(tab, text="Save API Key", command=self.save_api_keys)
        self.save_settings_button.pack(pady=20)
        self.serpapi_status_var = ctk.StringVar(value="Not configured")
        self.serpapi_status_indicator = ctk.CTkFrame(tab, width=15, height=15, corner_radius=10, fg_color="gray")
        self.serpapi_status_indicator.pack(pady=5)
        ctk.CTkLabel(tab, textvariable=self.serpapi_status_var).pack(pady=5)
        self.test_connection_button = ctk.CTkButton(tab, text="Test Connection", command=self.test_api_connections)
        self.test_connection_button.pack(pady=10)

    def toggle_show_serpapi_key(self):
        self.serpapi_key_entry.configure(show="" if self.serpapi_show_var.get() else "•")

    def generate_keywords(self):
        seed_keyword = self.keyword_entry.get().strip()
        if not seed_keyword:
            messagebox.showwarning("Error", "Enter a seed keyword.")
            return
        self.status_var.set("Generating...")
        self.progress.set(0)
        self.generate_button.configure(state="disabled")
        def generate_in_thread():
            keywords = self.generator.generate_keywords(
                seed_keyword, self.count_var.get(), self.include_prefixes_var.get(),
                self.include_suffixes_var.get(), self.include_questions_var.get(), self.include_api_data_var.get()
            )
            self.results_text.delete("1.0", "end")
            self.results_text.insert("1.0", "\n".join(keywords))
            self.status_var.set(f"Generated {len(keywords)} keywords")
            self.progress.set(1)
            self.generate_button.configure(state="normal")
        threading.Thread(target=generate_in_thread, daemon=True).start()

    def copy_to_clipboard(self):
        text = self.results_text.get("1.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status_var.set("Copied")
            messagebox.showinfo("Success", "Successfully copied to clipboard!")

    def save_to_file(self):
        text = self.results_text.get("1.0", "end").strip()
        if text:
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            filename = f"keywords_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.txt"
            file_path = os.path.join(desktop_path, filename)
            with open(file_path, "w", encoding="utf-8") as f:
              f.write(text)
            self.status_var.set(f"Saved to {file_path}")
            messagebox.showinfo("Success", "Successfully saved to Desktop!")

    def save_api_keys(self):
        api_keys = {"serpapi": self.serpapi_key_var.get()}
        with open("api_config.json", "w", encoding="utf-8") as f:
            json.dump(api_keys, f)
        self.serpapi_source.api_key = self.serpapi_key_var.get()
        self.status_var.set("API key saved")
        self.update_api_status()

    def load_api_keys(self):
        if os.path.exists("api_config.json"):
            with open("api_config.json", "r", encoding="utf-8") as f:
                api_keys = json.load(f)
                self.serpapi_key_var.set(api_keys.get("serpapi", ""))
                self.serpapi_source.api_key = api_keys.get("serpapi", "")
            self.update_api_status()

    def test_api_connections(self):
        self.status_var.set("Testing...")
        if self.serpapi_source.api_key:
            response = requests.get("https://serpapi.com/search.json", params={"q": "test", "api_key": self.serpapi_source.api_key})
            self.serpapi_status_var.set("Connected" if response.status_code == 200 else "Failed")
            self.serpapi_status_indicator.configure(fg_color="green" if response.status_code == 200 else "red")
        else:
            self.serpapi_status_var.set("Not configured")
            self.serpapi_status_indicator.configure(fg_color="gray")
        self.status_var.set("Test complete")

    def update_api_status(self):
        self.serpapi_status_var.set("Configured" if self.serpapi_source.api_key else "Not configured")
        self.serpapi_status_indicator.configure(fg_color="yellow" if self.serpapi_source.api_key else "gray")

if __name__ == "__main__":
    app = SEOKeywordGeneratorApp()
    app.mainloop()