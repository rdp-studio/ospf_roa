import json
import time
import sys
import ipaddress

# Usage: python update_ospf.py <input_json> <output_json> <asn> <trust_anchor>

def deduplicate_prefixes(roas):
    """Remove less specific prefixes when more specific ones exist"""
    # Convert prefixes to network objects for comparison
    networks = []
    for i, roa in enumerate(roas):
        try:
            network = ipaddress.ip_network(roa['prefix'], strict=False)
            networks.append((network, i, roa))
        except ValueError:
            # Keep entries that can't be parsed as valid networks
            networks.append((None, i, roa))
    
    # Find prefixes to keep
    keep_indices = set()
    
    for i, (net1, idx1, roa1) in enumerate(networks):
        if net1 is None:
            # Keep entries that couldn't be parsed
            keep_indices.add(idx1)
            continue
            
        is_redundant = False
        for j, (net2, idx2, roa2) in enumerate(networks):
            if i == j or net2 is None:
                continue
                
            # Check if net1 is contained within net2 (net1 is more specific)
            # or if net2 is contained within net1 (net2 is more specific)
            if net1.subnet_of(net2):
                # net1 is more specific than net2, so we should keep net1
                continue
            elif net2.subnet_of(net1):
                # net2 is more specific than net1, so net1 is redundant
                is_redundant = True
                break
        
        if not is_redundant:
            keep_indices.add(idx1)
    
    # Return only the non-redundant ROAs
    return [roas[i] for i in sorted(keep_indices)]

def main():
    if len(sys.argv) != 5:
        print("Usage: python update_ospf.py <input_json> <output_json> <asn> <trust_anchor>")
        sys.exit(1)

    input_json = sys.argv[1]
    output_json = sys.argv[2]
    asn = sys.argv[3]
    trust_anchor = sys.argv[4]

    with open(input_json, 'r') as f:
        data = json.load(f)

    roas = []
    for entry in data.get('NN', []):
        prefix = entry['prefix']
        maxlen = int(prefix.split('/')[1])
        roas.append({
            'asn': f'AS{asn}',
            'prefix': prefix,
            'maxLength': maxlen
        })

    # Deduplicate prefixes to remove less specific ones
    roas = deduplicate_prefixes(roas)

    output = {
        'metadata': {
            'counts': len(roas),
            'generated': int(time.time()),
            'valid': int(time.time())
        },
        'roas': roas
    }

    with open(output_json, 'w') as f:
        json.dump(output, f, indent=2)

if __name__ == "__main__":
    main()
