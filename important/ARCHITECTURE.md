# Compust architecture

The initial backend follows a deliberately small flow:

```text
FastAPI route
  -> SQLAlchemy session
  -> existing MySQL compust database
```

Scraping, parsing, normalization, persistence, profiles, and matching will be
introduced incrementally after this foundation is verified. The scraper will
separate source discovery from job extraction and will treat each stored career
URL as an entry point rather than assuming it represents one complete page.
