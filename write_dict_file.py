
def d_write(outfile, d):
      out = open(outfile, "a")
      items = [(v, k) for k, v in d.items()]
      items.sort()
      for v, k in items:
          #out.write(k,v)
          print(k,v, file=out) # file=open(outfile, "a")
          #print >>out, k, v
      out.close()

#d_write("test.txt", {"which": 2, "world":13})
