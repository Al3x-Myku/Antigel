# MetaMask NFT Display Issue - Solution

## The Problem

MetaMask has trouble displaying NFTs that use `data:application/json` URIs (on-chain metadata). MetaMask expects NFT metadata to be served from an HTTP/HTTPS endpoint.

Current contract returns: `data:application/json,{"name":"..."}`  
MetaMask expects: `https://example.com/metadata/1`

## Why This Happens

1. **MetaMask caching** - Very aggressive caching of NFT metadata
2. **Data URI support** - Limited support for `data:` URIs in NFT metadata
3. **Refresh delays** - Can take 30+ minutes or never refresh properly

## Solutions

### Solution 1: Use the Metadata Server (Recommended for Development)

Run the local metadata server to serve NFT data in a format MetaMask likes:

```bash
# Install dependencies
pip install -r requirements-server.txt

# Run the server
python3 metadata_server.py
```

The server will run at `http://localhost:5000` and provide endpoints like:
- `http://localhost:5000/metadata/1` - NFT #1 metadata
- `http://localhost:5000/metadata/2` - NFT #2 metadata

**Note:** This only works locally. For production, you'd need to host this on a public server.

### Solution 2: Deploy to IPFS (Recommended for Production)

For a production-ready solution, you should:

1. Generate NFT metadata JSON files
2. Upload images to IPFS
3. Upload metadata JSON to IPFS
4. Update contract to return IPFS URLs like: `ipfs://Qm.../metadata.json`

### Solution 3: Wait for MetaMask (Not Reliable)

Sometimes MetaMask will eventually display the metadata, but it can take:
- 5-30 minutes for initial load
- Requires removing and re-adding the NFT
- May never work properly with data URIs

### Solution 4: View in Your App (Current Working Solution)

Your SideQuests web app already displays NFT metadata perfectly! The data is there and correct - it's just MetaMask that won't display it.

Users can:
1. View their achievements in the SideQuests app
2. Click on any achievement to see full details
3. See images, descriptions, and all attributes

## What's Working

✅ Contract stores all metadata correctly  
✅ Contract returns proper JSON with images and descriptions  
✅ Your web app displays NFTs beautifully  
✅ NFT data is on-chain and verifiable  

## What's Not Working

❌ MetaMask won't display data URI metadata properly  
❌ No public testnet NFT explorers (OpenSea dropped testnet support)  

## Current NFT Metadata

Your NFTs DO have images and descriptions! Here's what's stored:

**NFT #1 - First Quest**
- Image: https://img.icons8.com/fluency/96/000000/bullseye.png
- Description: "Completed your first task on SideQuests"
- Rarity: Common

**NFT #2 - Token Collector**
- Image: https://img.icons8.com/fluency/96/000000/money-bag.png
- Description: "Earned 100 HLP tokens"  
- Rarity: Common

The metadata IS there - MetaMask just won't show it from a data URI.

## For Production Deployment

When deploying to mainnet or for a real product:

1. **Use IPFS for metadata** - Most reliable for wallet support
2. **Host a metadata API** - Use services like Alchemy NFT API or your own server
3. **Update contract** - Modify `tokenURI()` to return IPFS or HTTPS URLs

## Testing Your NFTs

To verify your NFTs work correctly:

```bash
# Run the metadata server
python3 metadata_server.py

# In another terminal, test the endpoints
curl http://localhost:5000/metadata/1
curl http://localhost:5000/metadata/2
```

You'll see the full metadata with images and descriptions!
