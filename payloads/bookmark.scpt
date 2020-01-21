property newBookmark : "https://stackoverflow.com"
property theTitle : "Important docs"
property bookmarkFolder : "Bookmarks Bar"

tell application "Google Chrome"
  try
      tell active tab of window 1
          repeat while loading is true
              delay 0.3
          end repeat
      end tell
  end try
  tell its bookmark folder bookmarkFolder
      set theResult to make new bookmark item with properties {URL:newBookmark}
      set title of theResult to theTitle
  end tell
end tell
