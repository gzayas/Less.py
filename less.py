#!/usr/bin/python
import curses
import sys

  
class WindowAttr():
    def __init__(self, y, x, tab_size):
        self.y = y
        self.x = x
        self.tab_size = tab_size
        

class Buffer():
    def __init__(self, content):
        self.__top = 0
        self.__content = self.__orig_content = content

    def set_win_attr(self, win_attr):
        self.__win_attr = win_attr
        self.__prepare_content()

    def search_forward(self, expr, rows_from_top=0):
        """positions the window on the first line that contains the expr given moving forward, if not found it leaves the window at its current location. Returns a triple containing the amount of row moved, a flag whether it did actually find something, a flag to mark the end of the buffer and the window itself"""
        new_top = self.__top+rows_from_top
        for line in self.__content[self.__top+rows_from_top:]:
            if line.find(expr)>=0:
                moved = new_top - self.__top
                self.__top = new_top
                return (moved, True, self.__at_end(), self.get_window()[1])
            new_top += 1
        return (0, False, self.__at_end(), self.get_window()[1])

    def search_backward(self, expr, rows_from_top=0):
        """positions the window on the first line that contains the expr given moving backwards, if not found it leaves the window at its current location. Returns a triple containing the amount of row moved, a flag whether it did actually find something, a flag to mark the end of the buffer and the window itself"""
        new_top = self.__top-rows_from_top
        for line in list(reversed(self.__content[0:self.__top-rows_from_top])):
            if line.find(expr)>=0:
                moved = self.__top - new_top + rows_from_top + 1
                self.__top = new_top - 1
                return (-moved, True, self.__at_end(), self.get_window()[1])
            new_top -= 1
        return (0, False, self.__at_end(), self.get_window()[1])

    def get_window(self):
        """returns the current window plus a flag marking whether we are at the end of the buffer. Result is returned in a pair as (flag, window)"""
        return (self.__at_end(), self.__content[self.__top:self.__top+self.__win_attr.y])

    def slide_down(self, rows):
        """slides the window down by 'rows' lines returning a triple with how much it has actually moved, whether it is at the end of the buffer and the actual window"""
        if len(self.__content) <= self.__top+self.__win_attr.y:
            return (0, True, self.__content[self.__top:self.__top+self.__win_attr.y])
        rem = len(self.__content) - (self.__top+self.__win_attr.y)
        self.__top = self.__top + min(rem, rows)
        return (rows, self.__at_end(), self.__content[self.__top:self.__top+self.__win_attr.y])

    def slide_up(self, rows):
        """slides the window up by rows lines returning a triple with how much it has actually moved, whether it is at the end of the buffer and the actual window"""
        if self.__top <= 0:
            return (0, self.__at_end(), self.__content[self.__top:self.__top+self.__win_attr.y])
        self.__top = self.__top - 1
        return (-1, self.__at_end(), self.__content[self.__top:self.__top+self.__win_attr.y])

    def __at_end(self):
        return len(self.__content) <= self.__top+self.__win_attr.y

    #note this ties the buffer to a single view but it's the simplest approach that works for this small programm
    def __prepare_content(self):
        """transforms the original content into one that can be used to display on the screen by ensuring minimum size, line width, tabs chars, etc. """
        def expandtabs(orig_content,  tab_size):
            """converts tabs to spaces to avoid issues when cutting lines to feet the screen size"""
            content = []
            for line in orig_content:
                content.append(line.expandtabs(tab_size))
            return content

        def adjust_up_to(content, width):
            """break up long lines to fit the screen width"""
            result = []
            for line in content:
                result += break_line(line, width)
            return result
            
        def break_line(line, width):
            """breaks a line into multiple lines respecting the max width"""
            if len(line) <= width:
                return [line]
            return [line[0:width]] + break_line(line[width:], width)

        self.__content = expandtabs(self.__orig_content, self.__win_attr.tab_size)
        self.__content = adjust_up_to(self.__content, self.__win_attr.x)

                    

class Display():
    """class which implements the  interaction with curses"""

    def __enter__(self):
        self.__screen = self.__prepare_screen()
        self.__win_attr = self.__get_win_attr()
        return self

    def __exit__(self, ext_type, ext_value, traceback):
        curses.endwin()
        
    def __prepare_screen(self):
        screen = curses.initscr()
        screen.scrollok(True) 
        curses.noecho()
        curses.nonl()
        curses.cbreak()
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
        return screen

    def refresh_win_attr(self):
        """This function determines the width/height and tab size of the current window. Should be called everytime a resize is detected"""
        self.__win_attr = self.__get_win_attr()
        return self.__win_attr

    def __get_win_attr(self):
        # is there any other better way of figuring out \t's length
        self.__screen.addstr(0,0,'\t')
        self.__screen.refresh()
        (ay,ax) = self.__screen.getyx()
        self.__screen.clear()
        (y, x) = self.__screen.getmaxyx()
        return WindowAttr(y-1,x,ax)

    def show_window(self, window, expr):
        """Displays the content of window highlighting the expression provided"""
        self.__show_window(0, self.__win_attr.y, self.__pad(window), expr)

    def scroll(self, window, m, expr):
        """scrolls the window m rows upwards or downwards (depending on the sign of m, ensures expr (if not empty) is highlighted"""
        if (m < 0):
            self.__scroll_up(self.__pad(window), m, expr)
        else: # also handles the case where we do not need to move (i.e. m==0) but do need to highlight the expression passed
            self.__scroll_down(self.__pad(window), m, expr)

    def __show_highlighting(self, window, expr):
        """shows the window highlighting the expr given"""
        for i in range(0,len(window)):
            self.__screen.move(i,0)
            if window[i].find(expr) >=0:
                offset = 0
                while offset<len(window[i]):
                    idx = window[i].find(expr, offset)
                    if idx<0:
                        self.__screen.addstr(window[i][offset:])
                        break
                    self.__screen.addstr(window[i][offset:idx])
                    self.__screen.addstr(expr, curses.A_REVERSE)
                    offset = idx+len(expr)
            else:
                self.__screen.addstr(i, 0, window[i])

    def __show_window(self, s, e, window, expr):
        if expr!='':
            self.__show_highlighting(window, expr)
        else:
            for i in range(s,e):
                self.__screen.addstr(i, 0, window[i])
        self.show_at_ctr_line(':')


    def __pad(self, window):
        """ensures window is at least as long as the expected height"""
        new_w = window
        diff  = self.__win_attr.y - len(window)
        for i in range(0,diff):
            new_w.append('~'.ljust(self.__win_attr.x-1))
        return new_w

    def __scroll_down(self, window, m, expr):
        if m < self.__win_attr.y:
            rows = m%self.__win_attr.y
            self.__screen.scroll(m)
            self.__show_window(self.__win_attr.y-rows, self.__win_attr.y, window, expr)
        else:
            self.__show_window(0, self.__win_attr.y, window, expr)

    def __scroll_up(self, window, m, expr):
        if m < 0:
            self.__screen.scroll(m)
            self.__show_window(0, -m+1, window, expr)

    def show_at_ctr_line(self, msg, attr=0):
        """Shows the given msg at the control line (last line in the window)"""
        self.__screen.addstr(self.__win_attr.y, 0,''.ljust(self.__win_attr.x-1))
        self.__screen.addstr(self.__win_attr.y, 0, msg, attr)
        self.__screen.refresh()

    def get_event(self):
        """blocks waiting for the next input from the current window, returning the event that the user triggered (a character, a resize action, etc.)"""
        return self.__screen.getch()

    def win_attr(self):
        return self.__win_attr
            
class Controller():
    __FORWARD=True   
    __BACKWARD=False    
    def __init__(self, display, buffer):
        self.__buffer = buffer
        self.__display = display
        self.__last_search = ''
        self.__swallow_return=False
        self.__search_direction=self.__FORWARD

    def loop(self):
        self.__refresh_display()
        while True:
            c = self.__display.get_event()
            if c in (ord('j'), ord(' ')):
                self.slide_down(self.__display.win_attr().y if c==ord(' ') else 1)
            elif c in (ord('\r'), ord('\n')):
                if self.__swallow_return:
                    self.__display.show_at_ctr_line(':')
                    self.__swallow_return = False
                else:
                    self.slide_down(1)
            elif c == ord('k'):
                self.slide_up()
            elif c in (ord('/'), ord('?')):
                self.__start_search_mode(chr(c))
            elif c == ord('n'):
                self.__search_move_next()
            elif c == ord('N'):
                self.__search_move_prev()
            elif c == ord('q'):
                return
            elif c == curses.KEY_RESIZE:
                self.__refresh_display()

    def __refresh_display(self):
        self.__display.refresh_win_attr()
        self.__buffer.set_win_attr(self.__display.win_attr())
        (at_end, window) = self.__buffer.get_window()
        self.__display.show_window(window, self.__last_search)
        if at_end:
            self.__display.show_at_ctr_line('(END)', curses.A_REVERSE)

    def slide_down(self, rows):
        (m, at_end, window) = self.__buffer.slide_down(rows)
        self.__display.scroll(window, m, self.__last_search)
        if at_end:
            self.__display.show_at_ctr_line('(END)', curses.A_REVERSE)

    def slide_up(self):
        (m, at_end, window) = self.__buffer.slide_up(1)
        self.__display.scroll(window, m, self.__last_search)
        if at_end:
            self.__display.show_at_ctr_line('(END)', curses.A_REVERSE)
        else:
            self.__display.show_at_ctr_line(':')

    def __start_search_mode(self, char):
        self.__search_direction = self.__FORWARD if char=='/' else self.__BACKWARD
        self.__display.show_at_ctr_line(char)
        expr = ''
        while True:
            c = self.__display.get_event()
            if c in (ord('\n'), ord('\r')) :
                advance_by = 0
                if expr =='':
                    expr = self.__last_search
                    advance_by = 1
                self.__last_search = expr
                self.__do_search_now(advance_by)
                break
            elif c == 127: #backspace/DEL?
                expr = expr[0:-1]
                self.__display.show_at_ctr_line('/'+expr)
            else:
                expr = expr + chr(c)
                self.__display.show_at_ctr_line('/'+expr)

    def __do_search_now(self, rows_from_top=0):
        if (self.__search_direction == self.__FORWARD):
            (m, found, at_end, window) = self.__buffer.search_forward(self.__last_search, rows_from_top)
        else:
            (m, found, at_end, window) = self.__buffer.search_backward(self.__last_search, rows_from_top)
            
        if found:
            self.__display.scroll(window, m, self.__last_search)
            if at_end:
                self.__display.show_at_ctr_line('(END)', curses.A_REVERSE)
        else:
            self.__swallow_return = True
            self.__display.show_window(window, self.__last_search)
            self.__display.show_at_ctr_line("Patter not found  (press RETURN)", curses.A_REVERSE)

    def __search_move_next(self):
        if self.__last_search=='':
            self.__display.show_at_ctr_line('No previous search', curses.A_REVERSE)
            return
        self.__do_search_now(1)

    def __search_move_prev(self):
        def _toggle_direction(dir):
            return self.__FORWARD if dir == self.__BACKWARD else self.__BACKWARD            
        if self.__last_search=='':
            self.__display.show_at_ctr_line('No previous search', curses.A_REVERSE)
            return
        self.__search_direction = _toggle_direction(self.__search_direction)
        self.__do_search_now(1)
        self.__search_direction = _toggle_direction(self.__search_direction)
        

def main(argv):
    file_name = argv[0]
    try:
        stream = file(file_name, 'r')
    except IOError as e:
        sys.stderr.write(file_name + ': ' + e.strerror + '\n')
        exit(1)

    buffer = Buffer(stream.readlines())
    with Display() as display:
        controller = Controller(display, buffer)
        controller.loop()

if __name__ == "__main__":
    main(sys.argv[1:])
