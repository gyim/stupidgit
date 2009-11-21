import wx
import git
import platformspec
from util import *

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
    def __init__(self, parent, id, allowMultiple=False):
        wx.ScrolledWindow.__init__(self, parent, -1, style=wx.SUNKEN_BORDER)
        self.SetBackgroundColour('WHITE')
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftClick)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightClick)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)
        self.repo = None
        self.selection = []
        self.mainRepo = None
        self.mainRepoSelection = []
        self.allowMultiple = allowMultiple

    def SetRepo(self, repo):
        # Save selection if the last repo was the main repo
        if self.repo and self.repo == self.mainRepo:
            self.mainRepo = self.repo
            self.mainRepoSelection = [ self.rows[row][0].commit.sha1 for row in self.selection ]

        # Clear selection, scroll to top
        repo_changed = (self.repo != repo)
        if repo_changed:
            self.selection = []
            self.Scroll(0, 0)

        # Save main repo
        if not repo.parent:
            self.mainRepo = repo

        # Load commits
        self.repo = repo
        self.commits = self.repo.get_log(['--topo-order', '--all'])
        self.CreateLogGraph()

        # If this is a submodule, select versions that are referenced
        # by the parent module
        if repo_changed and self.repo != self.mainRepo:
            for version in self.mainRepoSelection:
                submodule_version = self.repo.parent.get_submodule_version(self.repo.name, version)
                if submodule_version:
                    rows = [ r for r in self.rows if r[0].commit.sha1 == submodule_version ]
                    if rows:
                        self.selection.append(self.rows.index(rows[0]))

        # Setup UI
        self.SetVirtualSize((-1, (len(self.rows)+1) * LINH))
        self.SetScrollRate(LINH, LINH)
        self.Refresh()
    
    def CreateLogGraph(self):
        rows = []  # items: (node, edges)
        nodes = {} # commit => GraphNode
        lanes = []
        color = 0

        self.rows = rows
        self.columns = 0
        self.nodes = nodes
        
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
                            if (yy < node.y and n.x == edge.x) or (len(edges) > edge.x and edges[edge.x] != None):
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

        # References
        if self.repo.current_branch:
            self._add_reference(self.repo.head, self.repo.current_branch, REF_HEADBRANCH)
        else:
            self._add_reference(self.repo.head, 'DETACHED HEAD', REF_DETACHEDHEAD)

        if self.repo.main_ref:
            self._add_reference(self.repo.main_ref, 'MAIN/HEAD', REF_MODULE)
        if self.repo.main_merge_ref:
            self._add_reference(self.repo.main_merge_ref, 'MAIN/MERGE_HEAD', REF_MODULE)

        for branch,commit_id in self.repo.branches.iteritems():
            if branch != self.repo.current_branch:
                self._add_reference(commit_id, branch, REF_BRANCH)
        for branch,commit_id in self.repo.remote_branches.iteritems():
            self._add_reference(commit_id, branch, REF_REMOTE)
        for tag,commit_id in self.repo.tags.iteritems():
            self._add_reference(commit_id, tag, REF_TAG)

    def _add_reference(self, commit_id, refname, reftype):
        if commit_id not in git.commit_pool:
            return

        commit = git.commit_pool[commit_id]
        if commit not in self.nodes:
            return

        self.nodes[commit].references.append((refname, reftype))

    def OnPaint(self, evt):
        evt.Skip(False)

        if not self.repo:
            return

        # Setup drawing context
        pdc = wx.PaintDC(self)
        try:
            dc = wx.GCDC(pdc)
        except:
            dc = pdc

        dc.BeginDrawing()
        
        # Get basic drawing context details
        size = self.GetClientSize()
        clientWidth, clientHeight = size.GetWidth(), size.GetHeight()

        # Determine which commits to draw
        x, y, width, height = self.GetUpdateRegion().GetBox()
        start_x, start_y = self.CalcUnscrolledPosition(x, y)
        start_row, end_row = max(0, start_y/LINH-1), (start_y+height)/LINH+1

        # Setup pens, brushes and fonts
        commit_pen = wx.Pen(wx.Colour(0,0,0,255), width=2)
        commit_brush = wx.Brush(wx.Colour(255,255,255,255))
        commit_font = platformspec.Font(12)

        edge_pens = [ wx.Pen(wx.Colour(*c), width=2) for c in EDGE_COLORS ]
        
        selection_pen = wx.NullPen
        selection_brush = wx.Brush(wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT))

        ref_pens = [
            wx.Pen(wx.Colour(128,128,192,255), width=1),   # REF_BRANCH
            wx.Pen(wx.Colour(0,255,0,255), width=1),       # REF_REMOTE
            wx.Pen(wx.Colour(128,128,0,255), width=1),     # REF_TAG
            wx.Pen(wx.Colour(255,128,128,255), width=1),   # REF_HEADBRANCH
            wx.Pen(wx.Colour(255,0,0,255), width=1),       # REF_DETACHEDHEAD
            wx.Pen(wx.Colour(160,160,160,255), width=1)    # REF_MODULE
        ]
        ref_brushes = [
            wx.Brush(wx.Colour(160,160,255,255)), # REF_BRANCH
            wx.Brush(wx.Colour(128,255,128,255)), # REF_REMOTE
            wx.Brush(wx.Colour(255,255,128,255)), # REF_TAG
            wx.Brush(wx.Colour(255,160,160,255)), # REF_HEADBRANCH
            wx.Brush(wx.Colour(255,128,128,255)), # REF_DETACHEDHEAD
            wx.Brush(wx.Colour(192,192,192,255))  # REF_MODULE
        ]
        ref_font = platformspec.Font(9)

        # Draw selection
        dc.SetPen(selection_pen)
        dc.SetBrush(selection_brush)
        for row in self.selection:
            if start_row <= row <= end_row:
                x, y = self.CalcScrolledPosition(0, (row+1)*LINH)
                dc.DrawRectangle(0, y-LINH/2, clientWidth, LINH)

        # Offsets
        offx = COLW
        offy = LINH

        # Draw edges
        edges = set()
        for node,row_edges in self.rows[start_row:end_row+1]:
            edges.update(row_edges)
        for edge in edges:
            if not edge: continue

            dc.SetPen(edge_pens[edge.color % len(EDGE_COLORS)])
            if edge.style == EDGE_DIRECT:
                x1, y1 = self.CalcScrolledPosition( edge.src.x*COLW+offx, edge.src.y*LINH+offy )
                x2, y2 = self.CalcScrolledPosition( edge.dst.x*COLW+offx, edge.dst.y*LINH+offy )
                dc.DrawLine(x1, y1, x2, y2)
            elif edge.style == EDGE_BRANCH:
                x1, y1 = self.CalcScrolledPosition( edge.src.x*COLW+offx, edge.src.y*LINH+offy )
                x2, y2 = self.CalcScrolledPosition( edge.dst.x*COLW+offx, edge.src.y*LINH+offy-7 )
                x3, y3 = self.CalcScrolledPosition( edge.dst.x*COLW+offx, edge.dst.y*LINH+offy )
                dc.DrawLine(x1, y1, x2, y2)
                dc.DrawLine(x2, y2, x3, y3)
            elif edge.style == EDGE_MERGE:
                x1, y1 = self.CalcScrolledPosition( edge.src.x*COLW+offx, edge.src.y*LINH+offy )
                x2, y2 = self.CalcScrolledPosition( edge.x*COLW+offx, edge.src.y*LINH+offy-7 )
                x3, y3 = self.CalcScrolledPosition( edge.x*COLW+offx, edge.dst.y*LINH+offy+7 )
                x4, y4 = self.CalcScrolledPosition( edge.dst.x*COLW+offx, edge.dst.y*LINH+offy )
                dc.DrawLine(x1, y1, x2, y2)
                dc.DrawLine(x2, y2, x3, y3)
                dc.DrawLine(x3, y3, x4, y4)

        # Draw commits
        dc.SetPen(commit_pen)
        dc.SetBrush(commit_brush)
        for node,edges in self.rows[start_row:end_row+1]:
            # Draw commit circle/rectangle
            if node.style == NODE_MERGE:
                x = node.x*COLW + offx - COMW/2
                y = node.y*LINH + offy - COMW/2   
                xx, yy = self.CalcScrolledPosition(x, y)
                dc.DrawRectangle(xx, yy, COMW, COMW)
            else:
                x = node.x*COLW + offx
                y = node.y*LINH + offy
                xx, yy = self.CalcScrolledPosition(x, y)
                dc.DrawCircle(xx, yy, COMW/2)

            # Calculate column
            if node.y < len(self.rows)-1:
                text_column = max(len(edges), len(self.rows[node.y+1][1]))
            else:
                text_column = len(edges) if len(edges) > 0 else 1

            # Draw references
            msg_offset = 0

            for refname,reftype in node.references:
                dc.SetPen(ref_pens[reftype])
                dc.SetBrush(ref_brushes[reftype])
                dc.SetFont(ref_font)

                x = text_column*COLW + offx + msg_offset
                y = node.y*LINH + offy - LINH/2 + 1
                width,height = dc.GetTextExtent(refname)
                
                if reftype in [REF_HEADBRANCH, REF_DETACHEDHEAD, REF_MODULE]:
                    points = [
                        (x, y+LINH/2-1),
                        (x+6, y),
                        (x+10 + width, y),
                        (x+10 + width, y+LINH-3),
                        (x+6, y+LINH-3)
                    ]
                    x += 6
                    points = [ self.CalcScrolledPosition(*p) for p in points ]
                    points = [ wx.Point(*p) for p in points ]

                    dc.DrawPolygon(points)
                    msg_offset += width+14
                else:
                    xx, yy = self.CalcScrolledPosition(x, y)
                    dc.DrawRoundedRectangle(xx, yy, width + 4, LINH-2, 2)
                    msg_offset += width+8

                dc.SetPen(commit_pen)
                dc.SetBrush(commit_brush)
                xx, yy = self.CalcScrolledPosition(x+2, y+1)
                dc.DrawText(safe_unicode(refname), xx, yy)

            # Draw message
            dc.SetFont(commit_font)
            x = text_column*COLW + offx + msg_offset
            y = node.y*LINH + offy - LINH/2
            xx, yy = self.CalcScrolledPosition(x, y)
            
            if self.rows.index((node, edges)) in self.selection:
                dc.SetTextForeground(wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))

            dc.DrawText(safe_unicode(node.commit.short_msg), xx, yy)
            dc.SetTextForeground(wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOWTEXT))

        dc.EndDrawing()

    def OnLeftClick(self, e):
        e.StopPropagation()
        self.SetFocus()

        # Determine row number
        x, y = self.CalcUnscrolledPosition(*(e.GetPosition()))
        row = self.RowNumberByCoords(x, y)
        if row == None:
            return

        # Handle different type of clicks
        old_selection = list(self.selection)
        if self.allowMultiple and e.ShiftDown() and len(old_selection) >= 1:
            from_row = old_selection[0]
            to_row = row
            if to_row >= from_row:
                self.selection = range(from_row, to_row+1)
            else:
                self.selection = range(to_row, from_row+1)
                self.selection.reverse()
        elif self.allowMultiple and (e.ControlDown() or e.CmdDown()):
            if row not in self.selection:
                self.selection.insert(0, row)
        else:
            self.selection = [row]

        # Emit right click event
        event = CommitListEvent(EVT_COMMITLIST_SELECT_type, self.GetId())
        event.SetCurrentRow(row)
        event.SetSelection(self.selection)
        self.ProcessEvent(event)
        self.OnSelectionChanged(row, self.selection)

        # Redraw window
        self.Refresh()

    def OnRightClick(self, e):
        e.StopPropagation()
        self.SetFocus()

        # Determine row number
        x, y = self.CalcUnscrolledPosition(*(e.GetPosition()))
        row = self.RowNumberByCoords(x, y)
        if row == None:
            return

        # Emit right click event
        event = CommitListEvent(EVT_COMMITLIST_RIGHTCLICK_type, self.GetId())
        event.SetCurrentRow(row)
        event.SetSelection(self.selection)
        event.SetCoords( (e.GetX(), e.GetY()) )
        self.ProcessEvent(event)
        self.OnRightButtonClicked(row, self.selection)

    def OnKeyPressed(self, e):
        key = e.GetKeyCode()

        # Handle only UP and DOWN keys
        if key not in [wx.WXK_UP, wx.WXK_DOWN] or len(self.rows) == 0:
            e.Skip()
            return

        e.StopPropagation()

        # Get scrolling position
        start_col, start_row = self.GetViewStart()
        size = self.GetClientSize()
        height = size.GetHeight() / LINH

        if self.selection:
            # Process up/down keys
            current_row = self.selection[0]

            if key == wx.WXK_UP:
                next_row = max(current_row-1, 0)
            if key == wx.WXK_DOWN:
                next_row = min(current_row+1, len(self.rows)-1)

            # Process modifiers
            if e.ShiftDown() and self.allowMultiple:
                if next_row in self.selection:
                    self.selection.remove(current_row)
                else:
                    self.selection.insert(0, next_row)
            else:
                self.selection = [next_row]

        else:
            # Select topmost row of current view
            next_row = start_row
            if next_row < 0 or next_row > len(self.rows):
                return

            self.selection = [next_row]

        # Scroll selection if necessary
        if next_row < start_row:
            self.Scroll(start_col, next_row-1)
        elif next_row > start_row + height - 1:
            self.Scroll(start_col, next_row-height+2)

        # Emit selection event
        event = CommitListEvent(EVT_COMMITLIST_SELECT_type, self.GetId())
        event.SetCurrentRow(next_row)
        event.SetSelection(self.selection)
        self.ProcessEvent(event)
        self.OnSelectionChanged(next_row, self.selection)

        self.Refresh()

    def RowNumberByCoords(self, x, y):
        row = (y+LINH/2) / LINH - 1

        if row < 0 or row >= len(self.rows):
            return None
        else:
            return row

    def CommitByRow(self, row):
        return self.rows[row][0].commit

    # Virtual event handlers
    def OnSelectionChanged(self, row, selection):
        pass

    def OnRightButtonClicked(self, row, selection):
        pass

EVT_COMMITLIST_SELECT_type = wx.NewEventType()
EVT_COMMITLIST_SELECT = wx.PyEventBinder(EVT_COMMITLIST_SELECT_type, 1)

EVT_COMMITLIST_RIGHTCLICK_type = wx.NewEventType()
EVT_COMMITLIST_RIGHTCLICK = wx.PyEventBinder(EVT_COMMITLIST_RIGHTCLICK_type, 1)

class CommitListEvent(wx.PyCommandEvent):
    def __init__(self, eventType, id):
        wx.PyCommandEvent.__init__(self, eventType, id)
        self.selection = None
        self.currentRow = None
        self.coords = (None, None)

    def GetCurrentRow(self):
        return self.currentRow

    def SetCurrentRow(self, currentRow):
        self.currentRow = currentRow

    def GetSelection(self):
        return self.selection

    def SetSelection(self, selection):
        self.selection = selection

    def SetCoords(self, coords):
        self.coords = coords

    def GetCoords(self):
        return self.coords

NODE_NORMAL   = 0
NODE_BRANCH   = 1
NODE_MERGE    = 2
NODE_JUNCTION = 3

REF_BRANCH       = 0
REF_REMOTE       = 1
REF_TAG          = 2
REF_HEADBRANCH   = 3
REF_DETACHEDHEAD = 4
REF_MODULE       = 5
class GraphNode(object):
    def __init__(self, commit):
        self.commit = commit
        self.x = None
        self.y = None
        self.color = None

        self.parent_edges = []
        self.child_edges  = []
        self.references   = []

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

