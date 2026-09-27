"""Read pixel size and optics from Zeiss .czi metadata (no czifile dependency)."""
import re


def czi_meta(path):
    b = open(path, 'rb').read()
    i = b.find(b'<ImageDocument>')
    j = b.find(b'</ImageDocument>', i)
    xml = b[i:j].decode('utf-8', 'replace') if i >= 0 else ''
    out = {}
    m = re.search(r'<Distance Id="X">\s*<Value>([^<]+)</Value>', xml)
    if m:
        out['m_per_px'] = float(m.group(1))
        out['px_per_mm'] = 1e-3 / float(m.group(1))
    for tag in ['TotalMagnification', 'AcquisitionDateAndTime']:
        m = re.search(rf'<{tag}>([^<]+)</{tag}>', xml)
        if m:
            out[tag] = m.group(1)
    m = re.search(r'<ZoomSetting>.*?<Zoom>([^<]+)</Zoom>', xml, re.S) or re.search(r'Id="Zoom"[^>]*>\s*<[^>]*>([^<]+)<', xml)
    zs = re.findall(r'<(?:Zoom|ZoomFactor)>([\d.]+)</', xml)
    if zs:
        out['zoom'] = zs[0]
    ob = re.findall(r'<ObjectiveName>([^<]+)</ObjectiveName>', xml)
    if ob:
        out['objective'] = ob[0]
    return out


if __name__ == '__main__':
    import sys
    for p in sys.argv[1:]:
        print(p, czi_meta(p))
