"""Image-sourcing experiment: find product images for beverages.

Reads beverage records (discovery outputs or catalog exports), queries
approved sources for candidate images, and evaluates product identity
and reuse rights independently. Writes structured outputs under
output/images/. Never modifies discovery state or production data.

No image binaries are downloaded or retained during discovery; only
URLs and metadata are recorded.
"""
