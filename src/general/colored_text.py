# from pygments import highlight
# from pygments.lexers import PythonLexer
# from pygments.formatters import HtmlFormatter
from datetime import datetime


tab = "    "


class Coloring:

    def css(self, n):
        return F"\t{self.html_color_name_list[n]} {{color:  {self.html_color_list[n]};}}\n"

    # =======================================================
    # TERMINAL COLORS WITH ANSI COLOR CODE
    # =======================================================

    end = '\033[0m'
    Black = '\033[90m'
    # White = '\033[97m'
    White = '\033[38;5;015m'

    # Brown = '\033[38;5;166m'
    Brown = '\033[38;5;130m'
    Orange = '\033[38;5;208m'
    # Yellow = '\033[93m'
    Yellow = '\033[38;5;011m'

    # Magenta = '\033[95m'
    Magenta = '\033[38;5;013m'
    Pink = '\033[38;5;200m'
    # Red = '\033[91m'
    Red = '\033[38;5;009m'

    # Cyan = '\033[96m'
    # Blue = '\033[94m'
    Cyan = '\033[38;5;014m'
    Blue = '\033[38;5;033m'
    # Blue = '\033[38;5;012m'
    # DarkBlue = '\033[38;5;027m'
    Purple = '\033[38;5;093m'

    # Green = '\033[92m'
    Green = '\033[38;5;010m'
    LightGreen = '\033[38;5;190m'
    Green50 = '\033[38;5;048m'

    Color202 = '\033[38;5;202m'
    Color211 = '\033[38;5;211m'
    Color217 = '\033[38;5;217m'

    # =======================================================
    # HTML
    # =======================================================

    _VioletRed = "#F6358A"
    name_VioletRed = F"{'VioletRed':_<15}"

    _Grapefruit = '#DC381F'
    name_Grapefruit = F"{'Grapefruit':_<15}"

    _Chocolate = '#D2691E'
    name_Chocolate = F"{'Chocolate':_<15}"

    _VividOrange = '#ff5f00'
    name_VividOrange = F"{'VividOrange':_<15}"

    _DarkOrange = '#ff8700'
    name_DarkOrange = F"{'DarkOrange':_<15}"

    _CanaryYellow = '#FFEF00'
    name_CanaryYellow = F"{'CanaryYellow':_<15}"

    _GreenYellow = '#B1FB17'
    name_GreenYellow = F"{'GreenYellow':_<15}"

    _ParrotGreen = '#12AD2B'
    name_ParrotGreen = F"{'ParrotGreen':_<15}"

    _Mint = '#3EB489'
    name_Mint = F"{'Mint':_<15}"

    _Cyan = '#00FFFF'
    name_Cyan = F"{'Cyan':_<15}"

    _RoyalBlue = '#4169E1'
    name_RoyalBlue = F"{'RoyalBlue':_<15}"

    _PurpleFlower = '#A74AC7'
    name_PurpleFlower = F"{'PurpleFlower':_<15}"

    _FuchsiaPink = '#FF77FF'
    name_FuchsiaPink = F"{'FuchsiaPink':_<15}"

    _BlushRed = '#E56E94'
    name_BlushRed = F"{'BlushRed':_<15}"

    _DeepRose = '#FBBBB9'
    name_DeepRose = F"{'DeepRose':_<15}"

    _MauveTaupe = '#915F6D'
    name_MauveTaupe = F"{'MauveTaupe':_<15}"

    # ======================================

    _Olive = '#808000'
    name_Olive = F"{'Olive':_<15}"

    _Teal = '#008080'
    name_Teal = F"{'Teal':_<15}"

    _Lime = '#00ff00'
    name_Lime = F"{'Lime ':_<15}"

    _White = '#FFFFFF'
    name_White = F"{'White':_<15}"

    WhiteIdx = 15

    color_list = [
        Red,            Brown,      Color202,       Orange,     Yellow,
        LightGreen,     Green,      Green50,        Cyan,       Blue,
        Purple,         Pink,       Magenta,        Color211,   Color217,
        White
    ]

    # Fuchsia________ {color:  #ff00ff;}

    html_color_list = [
        _VioletRed, _Grapefruit, _Chocolate, _VividOrange, _DarkOrange, _CanaryYellow,
        _GreenYellow, _ParrotGreen, _Mint, _Cyan, _RoyalBlue, _PurpleFlower,
        _FuchsiaPink, _BlushRed, _DeepRose, _MauveTaupe, _DeepRose,

        _VioletRed, _Grapefruit, _Chocolate, _VividOrange, _DarkOrange, _CanaryYellow,
        _GreenYellow, _ParrotGreen, _Mint, _Cyan, _RoyalBlue, _PurpleFlower,
        _FuchsiaPink, _BlushRed, _DeepRose, _MauveTaupe, _DeepRose
    ]
    """
        VioletRed       {color:  #F6358A;}
        Grapefruit      {color:  #DC381F;}
        Chocolate       {color:  #D2691E;}
        VividOrange     {color:  #ff5f00;}
        DarkOrange      {color:  #ff8700;}
        CanaryYellow    {color:  #FFEF00;}
        GreenYellow     {color:  #B1FB17;}
        ParrotGreen     {color:  #12AD2B;}
        Mint            {color:  #3EB489;}
        Cyan            {color:  #00FFFF;}
        RoyalBlue       {color:  #4169E1;}
        PurpleFlower    {color:  #A74AC7;}
        FuchsiaPink     {color:  #FF77FF;}
        BlushRed        {color:  #E56E94;}
        DeepRose        {color:  #FBBBB9;}
        Mauve Taupe     {color:  #915F6D;}        
    """
    html_color_name_list = [
        name_VioletRed, name_Grapefruit, name_Chocolate, name_VividOrange, name_DarkOrange, name_CanaryYellow,
        name_GreenYellow, name_ParrotGreen, name_Mint, name_Cyan, name_RoyalBlue, name_PurpleFlower,
        name_FuchsiaPink, name_BlushRed, name_DeepRose, name_MauveTaupe,

        name_VioletRed, name_Grapefruit, name_Chocolate, name_VividOrange, name_DarkOrange, name_CanaryYellow,
        name_GreenYellow, name_ParrotGreen, name_Mint, name_Cyan, name_RoyalBlue, name_PurpleFlower,
        name_FuchsiaPink, name_BlushRed, name_DeepRose, name_MauveTaupe,
    ]

    def colored(self, n, text):
        if n < len(self.color_list):
            return str(F"{self.color_list[n]}{text}\033[0m")
        return str(F"\033[38;5;{n+20}m{text}\033[0m")

    def print_week_date(self, coloIndex=6, padding=120, message=None, fill: chr = '.', fill_type: chr = ">"):
        # EXAMPLE
        # .................................. Process started on week 02/53, Mon 09 Jan 2023 at 11:45:35 245270
        # ....................................................................................................
        message = ' Process started on week %U/53, %a %d %b %Y at %H:%M:%S %f' if message is None \
            else F" {message.strip()} week: %U/53, %a %d %b %Y %H:%M:%S %f"
        message = self.colored(coloIndex, message)
        print(F"\n\n{datetime.today().strftime(message):{fill}{fill_type}{padding + 15}}\n{'':{fill}>{padding}}\n")

    def html_colored(self, n, text):
        if n < len(self.html_color_list):
            return F"<{self.html_color_name_list[n]}>{text}</{self.html_color_name_list[n]}>"
        return F"<{self.name_White}>{text}</{self.name_White}>"

    def table_line(self, text_list):
        def apply(color_idx):
            return F"\t| {self.colored(color_idx, text_list[0]):>19}. {self.colored(color_idx, text_list[1]):26} " \
                   F"{self.colored(color_idx, text_list[2]):53} | "\
                   F"{self.colored(color_idx, text_list[3]):-^25}  {self.colored(color_idx, text_list[4]):^23}  "\
                   F"{self.colored(color_idx, text_list[5]):26} {self.colored(color_idx, text_list[6]):25} " \
                   F"{self.colored(color_idx, text_list[7]):55} | {self.colored(color_idx, text_list[8]):43} |\n"
        return apply

    def table_line_html(self, text_list):
        def apply(color_idx):
            return F"{tab}| {self.html_colored(color_idx, text_list[0]):>38}. " \
                   F"{self.html_colored(color_idx, text_list[1]):45} {self.html_colored(color_idx, text_list[2]):72} | "\
                   F"{self.html_colored(color_idx, text_list[3]):-^44}  {self.html_colored(color_idx, text_list[4]):^43}  "\
                   F"{self.html_colored(color_idx, text_list[5]):46} {self.html_colored(color_idx, text_list[6]):45} " \
                   F"{self.html_colored(color_idx, text_list[7]):74} | {self.html_colored(color_idx, text_list[8]):63} |\n"
        return apply


def test():
    print(f"{Coloring.Red}Warning: No active form remain. Continue?{Coloring.end}")
    print(f"{Coloring.Brown}Warning: No active form remain. Continue?{Coloring.end}")
    print(f"{Coloring.Color202}Warning: No active form remain. Continue?{Coloring.end}")
    print(f"{Coloring.Orange}Warning: No active form remain. Continue?{Coloring.end}")
    print(f"{Coloring.Yellow}Warning: No active form remain. Continue?{Coloring.end}")
    print(f"{Coloring.LightGreen}Warning: No active form remain. Continue?{Coloring.end}")
    print(f"{Coloring.Green}Warning: No active form remain. Continue?{Coloring.end}")
    print(f"7. {Coloring.Green50}Warning: No active form remain. Continue?{Coloring.end}")
    print(f"8. {Coloring.Cyan}Warning: No active form remain. Continue?{Coloring.end}")
    print(f"9. {Coloring.Blue}Warning: No active form remain. Continue?{Coloring.end}")
    print(f"{Coloring.Purple}Warning: No active form remain. Continue?{Coloring.end}")
    print(f"{Coloring.Pink}Warning: No active form remain. Continue?{Coloring.end}")
    print(f"{Coloring.Magenta}Warning: No active form remain. Continue?{Coloring.end}")
    print(f"{Coloring.Color211}Warning: No active form remain. Continue?{Coloring.end}")
    print(f"{Coloring.Color217}Warning: No active form remain. Continue?{Coloring.end}")

# test()
