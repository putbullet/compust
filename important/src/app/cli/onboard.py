import argparse
import json
import sys

from ..database import get_db
from ..schemas_onboarding import CompanyOnboardRequest
from ..services.onboarding_service import onboard_company_and_target


def main():
    parser = argparse.ArgumentParser(
        description="Onboard a new company and initial scrape target into Compust with automatic portal classification."
    )
    parser.add_argument("--name", required=True, help="Company name (e.g. 'Atlas Cloud')")
    parser.add_argument("--website", required=True, help="Company website URL (e.g. 'https://atlascloud.ma')")
    parser.add_argument("--careers", required=True, help="Careers portal URL (e.g. 'https://atlascloud.ma/careers')")
    parser.add_argument("--target-url", required=False, help="Specific target URL if different from careers URL")
    parser.add_argument("--country", default="MA", help="ISO country code (default: MA)")
    parser.add_argument("--interval", type=int, default=24, help="Scrape interval in hours (default: 24)")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")

    args = parser.parse_args()

    req = CompanyOnboardRequest(
        name=args.name,
        website_url=args.website,
        careers_url=args.careers,
        scrape_target_url=args.target_url,
        country_code=args.country,
        scrape_interval_hours=args.interval,
    )

    db_gen = get_db()
    db = next(db_gen)
    try:
        res = onboard_company_and_target(db, req)
        if args.json:
            print(res.model_dump_json(indent=2))
        else:
            print("==================================================")
            print(f" COMPUST ONBOARDING: {res.company_name} (ID: {res.company_id})")
            print("==================================================")
            print(f" Country:           {res.country_code}")
            print(f" Target URL:        {res.scrape_target_url}")
            print(f" Target ID:         {res.scrape_target_id}")
            print(f" Target Status:     {res.scrape_target_status}")
            print("----------------- Classification -----------------")
            print(f" Portal Type:       {res.classification.portal_type}")
            print(f" Pagination:        {res.classification.pagination_style}")
            print(f" Suggested Strategy:{res.classification.suggested_strategy_type}")
            print(f" Robots.txt Allowed:{res.classification.robots_txt_allowed}")
            print(f" Recommendation:    {res.classification.recommendation}")
            if res.classification.api_endpoints_detected:
                print(f" Detected APIs:     {', '.join(res.classification.api_endpoints_detected)}")
            print("==================================================")
    finally:
        db.close()


if __name__ == "__main__":
    main()
