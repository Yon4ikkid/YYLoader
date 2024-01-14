import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import net_api
import pytube
import sys
import threading
import asyncio


BACKGROUND_COLOR = 'black'
DEFAULT_BORDER_COLOR = 'DarkOrchid1'
DEFAULT_TEXT_COLOR = 'white'
DEFAULT_BORDER_THICKNESS = 2


class OptionListBox(tk.Listbox):
    def __init__(self, parent):
        super().__init__(parent, selectmode=tk.SINGLE, width=20, exportselection=False)

    def insert_options(self, options):
        self.delete(0, tk.END)
        for option in options[::-1]:
            self.insert(0, option)
        self.selection_set(first=0)

    def get_choice(self):
        return self.curselection()[0]


class MyApp(tk.Tk):
    def __init__(self):
        def __loop_runner(event_loop):
            asyncio.set_event_loop(event_loop)
            event_loop.run_forever()
        self.__api_event_loop = asyncio.new_event_loop()
        self.__api_thread = threading.Thread(target=__loop_runner, args=(self.__api_event_loop,))
        self.__api_thread.start()

        tk.Tk.__init__(self)
        self.title("YYLoader")
        self.__height = 600
        self.__width = 800
        self.resizable(0,0)
        self.configure(bg=BACKGROUND_COLOR)
        self.__download_target = None

        # Setup frames
        options_frame = tk.Frame(self, highlightcolor=DEFAULT_BORDER_COLOR, highlightbackground=DEFAULT_BORDER_COLOR, highlightthickness=DEFAULT_BORDER_THICKNESS,bg=BACKGROUND_COLOR, height=0.98*self.__height, width=0.30*self.__width)
        options_frame.grid(row=0, column=0, padx=(0.05 * self.__width,0), pady=0.01 * self.__height, rowspan=3)
        options_frame.grid_propagate(False)

        input_frame = tk.Frame(self, highlightcolor=DEFAULT_BORDER_COLOR, highlightbackground=DEFAULT_BORDER_COLOR, highlightthickness=DEFAULT_BORDER_THICKNESS,bg=BACKGROUND_COLOR, height=0.48*self.__height, width=0.60*self.__width)
        input_frame.grid(row=0, column=1, padx=0.05*self.__width, pady=(0.01 * self.__height,0))
        input_frame.grid_propagate(False)

        feedback_frame = tk.Frame(self, highlightcolor=DEFAULT_BORDER_COLOR, highlightbackground=DEFAULT_BORDER_COLOR, highlightthickness=DEFAULT_BORDER_THICKNESS,bg=BACKGROUND_COLOR, height=0.48*self.__height, width=0.60*self.__width)
        feedback_frame.grid(row=1, column=1, padx=0.05*self.__width, pady=0.01 * self.__height, rowspan=2)
        feedback_frame.grid_propagate(False)

        frame_title_font = ('Arial', 15, 'bold')
        subtitle_font = ('Arial', 11, 'bold')

        # Options Frame
        options_frame.columnconfigure((0,1,2), weight=1, minsize=self.__width*0.1)
        options_frame.rowconfigure((0,1,2,3,4,5), weight=1)
        options_frame_title = tk.Label(options_frame, text="Options", fg=DEFAULT_TEXT_COLOR, bg=BACKGROUND_COLOR, font=frame_title_font).grid(row=0, column=1)

        self.__audio_options = OptionListBox(options_frame)
        self.__audio_options.grid(row=2, column=0, columnspan=3)
        audio_label = tk.Label(options_frame, text="Available Audio", font=subtitle_font, bg=BACKGROUND_COLOR, fg=DEFAULT_TEXT_COLOR)
        audio_label.grid(row=1,column=0, columnspan=3)

        self.__video_options = OptionListBox(options_frame)
        self.__video_options.grid(row=4, column=0, columnspan=3)
        video_label = tk.Label(options_frame, text="Available Video", font=subtitle_font, bg=BACKGROUND_COLOR, fg=DEFAULT_TEXT_COLOR)
        video_label.grid(row=3,column=0, columnspan=3)


        # Input Frame
        input_frame.columnconfigure((0,1,2), weight=1)
        input_frame.rowconfigure((0,1,2), weight=1)

        values = ["Video and Audio", "Only Video", "Only Audio", "Audio in MP3"]
        self.__download_option = tk.StringVar()
        self.__download_option.set(values[0])
        download_option_menu = tk.OptionMenu(input_frame, self.__download_option, *values)
        download_option_menu.config(bg=DEFAULT_BORDER_COLOR, fg=DEFAULT_TEXT_COLOR, highlightbackground=BACKGROUND_COLOR)
        download_option_menu["menu"].config(bg=DEFAULT_BORDER_COLOR, fg=DEFAULT_TEXT_COLOR)
        download_option_menu.grid(row=2, column=1)
        download_option_menu.bind("<Enter>", MyApp.__hover_enter)
        download_option_menu.bind("<Leave>", MyApp.__hover_leave)
        download_button = tk.Button(input_frame, bg=DEFAULT_BORDER_COLOR, fg=DEFAULT_TEXT_COLOR, text='Download', highlightthickness=DEFAULT_BORDER_THICKNESS, command=self.__button_handler)
        download_button.grid(row=1, column=1)
        download_button.bind("<Enter>", MyApp.__hover_enter)
        download_button.bind("<Leave>", MyApp.__hover_leave)

        self.__input_line = tk.Entry(input_frame, bd=3, width=60)
        self.__input_line.grid(row=0, column=0,columnspan=3)
        self.__input_line.focus()

        # Output Frame
        feedback_frame.rowconfigure((0,1), weight=1)
        feedback_frame.columnconfigure((0,1,2), weight=1)
        self.__progress_bar = ttk.Progressbar(feedback_frame, orient=tk.HORIZONTAL, length=self.__width*0.6*0.9, mode='determinate')
        self.__progress_bar.grid(row=0, column=0, columnspan=3)
        self.__title_label = tk.Label(feedback_frame, bg=BACKGROUND_COLOR, fg=DEFAULT_TEXT_COLOR, font=subtitle_font)
        self.__title_label.grid(row=1, column=1)

        # Finalize
        self.bind("<ButtonRelease-3>", self.__paste)
        self.bind("<Return>", lambda e: self.__button_handler())
        self.after(100, self.__paste, None)


    def __await_future(self, future, handler): # TODO
        if future.done():
            handler(future)
        else:
            self.after(100, self.__await_future, future, handler)


    def __mp3_checkbox_event(self):
        if self.__mp3_var.get() == 1:
            self.__video_checkbox.deselect()
            self.__audio_checkbox.deselect()


    def __hover_enter(e):
        e.widget['background'] = BACKGROUND_COLOR
        e.widget['activebackground'] = BACKGROUND_COLOR
        e.widget['activeforeground'] = DEFAULT_BORDER_COLOR
        e.widget['foreground'] = DEFAULT_BORDER_COLOR
        e.widget['highlightbackground'] = DEFAULT_BORDER_COLOR
        e.widget['highlightcolor'] = DEFAULT_BORDER_COLOR

    def __hover_leave(e):
        e.widget['background'] = DEFAULT_BORDER_COLOR
        e.widget['foreground'] = DEFAULT_TEXT_COLOR
        e.widget['activebackground'] = DEFAULT_BORDER_COLOR
        e.widget['activeforeground'] = BACKGROUND_COLOR
        e.widget['highlightbackground'] = BACKGROUND_COLOR
        e.widget['highlightcolor'] = BACKGROUND_COLOR


    def __paste(self, event):
        try:
            text = self.clipboard_get()
        except tk.TclError:
            return
        self.__fetch_metadata(text)


    def __fetch_metadata(self, text):
        if 'playlist' in text:
            target_awaitable = net_api.PlaylistTarget.create(text, self.__progress_callback)
        else:
            target_awaitable = net_api.VideoTarget.create(text, self.__progress_callback)
        target_future = asyncio.run_coroutine_threadsafe(target_awaitable, self.__api_event_loop)

        def __inner(future):
            try:
                self.__download_target = future.result()
            except pytube.exceptions.PytubeError:
                return
            audio_options, video_options = self.__download_target.get_available_streams()
            self.__audio_options.insert_options(audio_options)
            self.__video_options.insert_options(video_options)
            self.__input_line.delete(0,tk.END)
            self.__input_line.insert(0, text)
            self.__title_label.configure(text=self.__download_target.get_name())
        self.__await_future(target_future, __inner)


    def __progress_callback(self, progress):
        self.__progress_bar['value'] = progress


    def __button_handler(self):
        if self.__download_target is None:
            return

        match self.__download_option.get():
            case "Video and Audio":
                suffix = ".mp4"
                download_handler = self.__download_target.download_combined_streams(self.__audio_options.get_choice(), self.__video_options.get_choice())
            case "Only Video":
                suffix = ".mp4"
                download_handler = self.__download_target.download_video(self.__video_options.get_choice())
            case "Only Audio":
                suffix = ".m4a"
                download_handler = self.__download_target.download_audio(self.__audio_options.get_choice())
            case "Audio in MP3":
                suffix = ".mp3"
                download_handler = self.__download_target.download_as_mp3(self.__audio_options.get_choice())
            case _:
                tk.messagebox.showerror("Input Error", "You have not chosen any download option.")
                return

        match self.__download_target.get_path_type():
            case "file":
                save_path = filedialog.asksaveasfilename(confirmoverwrite=True, initialfile=self.__download_target.get_name(), defaultextension=suffix, filetypes=[(f"File in {suffix}", f"*{suffix}")])
            case "directory":
                save_path = filedialog.askdirectory()
            case _:
                save_path = None
        
        if not save_path:
            return

        self.__download_target.set_save_path(save_path)
        future = asyncio.run_coroutine_threadsafe(download_handler, self.__api_event_loop)
        def __inner(future):
            self.close()
            sys.exit()
        self.__await_future(future, __inner)


    def close(self):
        self.__api_event_loop.call_soon_threadsafe(self.__api_event_loop.stop)
        while self.__api_event_loop.is_running(): pass
        self.__api_event_loop.close()
        
        
if __name__ == '__main__':
    app = MyApp()
    app.mainloop()
    app.close()
