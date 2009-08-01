import wx

COLW  = 12 # Column width
LINH  = 16 # Line height
COMW  = 8  # Commit width

EDGE_COLORS = [
    (  0,   0,  96, 200),
    (  0,  96,   0, 200),
    ( 96,   0,   0, 200),

    ( 64,  64,   0, 200),
    ( 64,  0,   64, 200),
    (  0,  64,  64, 200),

    (128, 192,   0, 200),
    (192, 128,   0, 200),
    ( 64,   0, 128, 200),
    (  0, 160,  96, 200),
    (  0,  96, 160, 200)
]

class CommitList(wx.ScrolledWindow):
    def __init__(self, parent, id):
        wx.ScrolledWindow.__init__(self, parent, -1, style=wx.SUNKEN_BORDER)
        self.SetBackgroundColour('WHITE')
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def SetRepo(self, repo):
        self.repo = repo
        self.commits = self.repo.get_log(['--topo-order', '--all'])
        self.CreateLogGraph()

        self.SetVirtualSize((600, (len(self.rows)+1) * LINH))
        self.SetScrollRate(20, 20)
    
    def CreateLogGraph(self):
        rows = []  # items: (node, edges)
        nodes = {} # commit => GraphNode
        lanes = []
        color = 0

        self.rows = rows
        self.columns = 0
        
        for y in xrange(len(self.commits)):
            # 1. Create node
            commit = self.commits[y]
            node = GraphNode(commit)
            nodes[commit] = node
            node.y = y
            rows.append((node, []))

            # 2. Determine column
            x = None

            # 2.1. search for a commit in lanes whose parent is c
            for i in xrange(len(lanes)):
                if lanes[i] and commit in lanes[i].commit.parents:
                    x = i
                    node.color = lanes[i].color
                    break

            # 2.2. if there is no such commit, put to the first empty place
            if x == None:
                node.color = color
                color += 1
                if None in lanes:
                    x = lanes.index(None)
                else:
                    x = len(lanes)
                    lanes.append(None)

            node.x = x
            self.columns = max(self.columns, x)

            # 3. Create edges
            for child_commit in commit.children:
                child = nodes[child_commit]
                edge = GraphEdge(node, child)
                node.child_edges.append(edge)
                child.parent_edges.append(edge)

                # 3.1. Determine edge style
                if child.x == node.x and lanes[x] == child:
                    edge.style = EDGE_DIRECT
                    edge.x = node.x
                    edge.color = child.color
                elif len(child_commit.parents) == 1:
                    edge.style = EDGE_BRANCH
                    edge.x = child.x
                    edge.color = child.color
                else:
                    edge.style = EDGE_MERGE
                    edge.color = node.color

                    # Determine column for merge edges
                    edge.x = max(node.x, child.x+1)
                    success = False
                    while not success:
                        success = True
                        for yy in xrange(node.y, child.y, -1):
                            n, edges = rows[yy]
                            if len(edges) > edge.x and edges[edge.x] != None:
                                edge.x += 1
                                success = False
                                break

                # 3.2. Register edge in rows
                for yy in xrange(node.y, child.y, -1):
                    n, edges = rows[yy]
                    if len(edges) < edge.x+1:
                        edges += [None] * (edge.x+1 - len(edges))
                    edges[edge.x] = edge

                self.columns = max(self.columns, edge.x)

            # 4. End those lanes whose parents are already drawn
            for i in xrange(len(lanes)):
                if lanes[i] and len(lanes[i].parent_edges) == len(lanes[i].commit.parents):
                    lanes[i] = None

            lanes[x] = node

    def OnPaint(self, evt):
        # Determine which commits to draw
        x, y, width, height = self.GetUpdateRegion().GetBox()
        start_x, start_y = self.CalcUnscrolledPosition(x, y)
        start_row, end_row = max(0, start_y/LINH-1), (start_y+height)/LINH+1

        # Setup drawing context
        pdc = wx.PaintDC(self)
        try:
            dc = wx.GCDC(pdc)
        except:
            dc = pdc

        dc.BeginDrawing()
        
        # Setup pens and brushes
        commit_pen = wx.Pen(wx.Colour(0,0,0,255), width=2)
        commit_brush = wx.Brush(wx.Colour(255,255,255,255))
        edge_pens = [ wx.Pen(wx.Colour(*c), width=2) for c in EDGE_COLORS ]
        text_pen = wx.Pen(wx.Colour(0,0,0,0))

        # Draw edges
        edges = set()
        for node,row_edges in self.rows[start_row:end_row+1]:
            edges.update(row_edges)
        for edge in edges:
            if not edge: continue

            dc.SetPen(edge_pens[edge.color % len(EDGE_COLORS)])
            if edge.style == EDGE_DIRECT:
                x1, y1 = self.CalcScrolledPosition( (edge.src.x+1)*COLW, (edge.src.y+1)*LINH )
                x2, y2 = self.CalcScrolledPosition( (edge.dst.x+1)*COLW, (edge.dst.y+1)*LINH )
                dc.DrawLine(x1, y1, x2, y2)
            elif edge.style == EDGE_BRANCH:
                x1, y1 = self.CalcScrolledPosition( (edge.src.x+1)*COLW, (edge.src.y+1)*LINH )
                x2, y2 = self.CalcScrolledPosition( (edge.dst.x+1)*COLW, (edge.src.y+1)*LINH-7 )
                x3, y3 = self.CalcScrolledPosition( (edge.dst.x+1)*COLW, (edge.dst.y+1)*LINH )
                dc.DrawLine(x1, y1, x2, y2)
                dc.DrawLine(x2, y2, x3, y3)
            elif edge.style == EDGE_MERGE:
                x1, y1 = self.CalcScrolledPosition( (edge.src.x+1)*COLW, (edge.src.y+1)*LINH )
                x2, y2 = self.CalcScrolledPosition( (edge.x+1)*COLW, (edge.src.y+1)*LINH-7 )
                x3, y3 = self.CalcScrolledPosition( (edge.x+1)*COLW, (edge.dst.y+1)*LINH+7 )
                x4, y4 = self.CalcScrolledPosition( (edge.dst.x+1)*COLW, (edge.dst.y+1)*LINH )
                dc.DrawLine(x1, y1, x2, y2)
                dc.DrawLine(x2, y2, x3, y3)
                dc.DrawLine(x3, y3, x4, y4)

        # Draw commits
        dc.SetPen(commit_pen)
        dc.SetBrush(commit_brush)
        for node,edges in self.rows[start_row:end_row+1]:
            # Draw commit circle/rectangle
            if node.style == NODE_MERGE:
                x = (node.x+1) * COLW - COMW/2
                y = (node.y+1) * LINH - COMW/2   
                xx, yy = self.CalcScrolledPosition(x, y)
                dc.DrawRectangle(xx, yy, COMW, COMW)
            else:
                x = (node.x+1) * COLW
                y = (node.y+1) * LINH
                xx, yy = self.CalcScrolledPosition(x, y)
                dc.DrawCircle(xx, yy, COMW/2)

            # Draw message
            if node.y < len(self.rows)-1:
                text_column = max(len(edges), len(self.rows[node.y+1][1]))
            else:
                text_column = len(edges)
            x = (text_column+1) * COLW
            y = (node.y+1) * LINH - 8
            xx, yy = self.CalcScrolledPosition(x, y)
            dc.DrawText(node.commit.short_msg, xx, yy)

        dc.EndDrawing()

NODE_NORMAL   = 0
NODE_BRANCH   = 1
NODE_MERGE    = 2
NODE_JUNCTION = 3
class GraphNode(object):
    def __init__(self, commit):
        self.commit = commit
        self.x = None
        self.y = None
        self.color = None

        self.parent_edges = []
        self.child_edges  = []

        if len(commit.parents) > 1 and len(commit.children) > 1:
            self.style = NODE_JUNCTION
        elif len(commit.parents) > 1:
            self.style = NODE_MERGE
        elif len(commit.children) > 1:
            self.style = NODE_BRANCH
        else:
            self.style = NODE_NORMAL

EDGE_DIRECT = 0
EDGE_BRANCH = 1
EDGE_MERGE  = 2
class GraphEdge(object):
    def __init__(self, src, dst):
        self.src = src
        self.dst = dst

        self.style = None
        self.color = None
        self.x = None
        self.color = None

