"""
Merge Kaggle sources with existing satellites by name matching.

This script takes the separately-created Kaggle documents and merges them
with existing UNOOSA/CelesTrak documents where the names match, following
the envelope pattern.
"""

import pandas as pd
from db import connect_mongodb, disconnect_mongodb, get_satellites_collection
import sys


def merge_kaggle_sources():
    """Match Kaggle documents to existing satellites by name and merge sources"""
    print("🔄 Merging Kaggle sources with existing satellites...\n")
    
    collection = get_satellites_collection()
    
    # Get all Kaggle documents
    kaggle_docs = list(collection.find({'sources.kaggle_1': {'$exists': True}}))
    print(f"📊 Found {len(kaggle_docs)} Kaggle-only documents")
    
    merged = 0
    unmatched = 0
    unmatched_list = []
    
    for kaggle_doc in kaggle_docs:
        kaggle_name = kaggle_doc['sources']['kaggle_1'].get('name', '').strip()
        kaggle_norad = kaggle_doc['sources']['kaggle_1'].get('norad_id', '')
        
        if not kaggle_name:
            unmatched += 1
            continue
        
        # Try to find matching document by name in other sources
        existing = collection.find_one({
            '$or': [
                {'sources.unoosa.name': kaggle_name},
                {'sources.celestrak.name': kaggle_name},
            ]
        })
        
        if existing:
            identifier = existing['identifier']
            
            # Add kaggle_1 source to existing document
            existing['sources']['kaggle_1'] = kaggle_doc['sources']['kaggle_1']
            existing['metadata']['sources_available'] = list(existing['sources'].keys())
            existing['metadata']['last_updated_at'] = kaggle_doc['metadata'].get('last_updated_at')
            
            # Update the document
            collection.replace_one({'identifier': identifier}, existing)
            
            # Delete the Kaggle-only document
            collection.delete_one({'identifier': kaggle_doc['identifier']})
            
            merged += 1
            if merged <= 20 or merged % 100 == 0:
                print(f"  ✓ Merged: {kaggle_name} (NORAD: {kaggle_norad})")
        else:
            unmatched += 1
            unmatched_list.append((kaggle_norad, kaggle_name))
    
    print(f"\n✅ Merge complete:")
    print(f"   Merged: {merged}")
    print(f"   Kept as separate: {unmatched}")
    
    if unmatched <= 50:
        print(f"\n📋 Unmatched Kaggle satellites:")
        for norad, name in unmatched_list:
            print(f"     {norad}: {name}")
    else:
        print(f"\n📋 Top 50 unmatched Kaggle satellites:")
        for norad, name in unmatched_list[:50]:
            print(f"     {norad}: {name}")
    
    # Final count
    total = collection.count_documents({})
    unoosa_count = collection.count_documents({'sources.unoosa': {'$exists': True}})
    celestrak_count = collection.count_documents({'sources.celestrak': {'$exists': True}})
    kaggle_count = collection.count_documents({'sources.kaggle_1': {'$exists': True}})
    multi_source = collection.count_documents({'sources': {'$where': 'Object.keys(this).length > 1'}})
    
    print(f"\n📈 Final database state:")
    print(f"   Total documents: {total}")
    print(f"   With UNOOSA: {unoosa_count}")
    print(f"   With CelesTrak: {celestrak_count}")
    print(f"   With Kaggle-1: {kaggle_count}")
    print(f"   Multi-source: {multi_source}")


if __name__ == "__main__":
    if not connect_mongodb():
        print("❌ Failed to connect to MongoDB")
        sys.exit(1)
    
    try:
        merge_kaggle_sources()
    finally:
        disconnect_mongodb()
