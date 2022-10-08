.PHONY: products reviewexcel tags crawl research

products:
	python -c "from scripts.products import create_all_products; create_all_products();"

reviewexcel:
	python -c "from scripts.reviews import create_judge_excel; create_judge_excel();"

tags:
	python -c "from scripts.products import update_product_tags; update_product_tags();"

crawl:
	python -c "from scripts.crawl import crawl_links; crawl_links();"

reviewfname:
	python -c "from scripts.reviews import create_specific_reviews; create_specific_reviews();"

research:
	python -c "from scripts.driver import make_research; make_research();"