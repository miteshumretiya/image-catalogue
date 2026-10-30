# Task 1: Design Specification

## 1.1 Application purpose

**Problem.** Most people have hundreds of photos sitting in folders with names like `IMG_4821.jpg`. File Explorer can show thumbnails, but it can't give a photo a proper title or tags, or let you rate your favourites, and finding "all the beach photos" means opening them one by one.

**Intended user.** Someone with a personal photo collection on their own computer (for example a student, a hobby photographer or a family archivist) who wants a simple, offline way to organise it. They are comfortable with normal desktop apps but are not technical.

**Main purpose.** Image Catalogue lets the user point the app at a folder and get a browsable table of all the images in it. They can then add titles, tags and ratings, search the collection and save it all to a catalogue file. Scanning a big folder takes time because every image has to be opened and shrunk to a thumbnail, so this happens in the background while the window stays usable.

## 1.2 Functional requirements

| ID | Requirement |
|----|-------------|
| FR1 | The user shall be able to choose a folder, and the application shall find every supported image in it, including sub-folders (JPG, PNG, GIF, BMP, WEBP, TIFF). |
| FR2 | The application shall generate a thumbnail and read the size, format and file size of each image in the background, without freezing the window. |
| FR3 | The application shall show scan progress (done / total) and allow the user to cancel a running scan. |
| FR4 | The application shall display all catalogued images in a table with a thumbnail, and allow sorting by any column. |
| FR5 | The user shall be able to select an image to see a larger preview and its details. |
| FR6 | The user shall be able to edit an image's title, tags and rating (0-5), and invalid input shall be rejected with a clear message. |
| FR7 | The user shall be able to search the catalogue by file name, title or tag. |
| FR8 | The user shall be able to remove an image from the catalogue (without deleting the file on disk). |
| FR9 | The user shall be able to save the catalogue to a file and open it again later. Broken or invalid files shall be reported, not crash the app. |
| FR10 | The application shall play a short sound when a scan finishes, and the user shall be able to turn this off. |

**Non-functional:** the window must stay responsive during scans; one unreadable file must not stop a scan; the user must be warned about unsaved changes before closing.

## 1.3 GUI design (wireframe)

```
+------------------------------------------------------------------------------+
| File  Edit  Tools  Help                                          <- menu bar |
+------------------------------------------------------------------------------+
| [Add Folder] [Save Catalogue] [Remove Image] | [Cancel Scan]     <- toolbar  |
+--------------------------------------------+---------------------------------+
| [ Search by name, title or tag...       ]  |  Preview                        |
| +----------------------------------------+ | +-----------------------------+ |
| |Preview| Name     | Title | Dims | ... ^| | |                             | |
| |[img]  | a.jpg    | Beach | 1920 |     || | |    large picture of the     | |
| |[img]  | b.png    | Cat   |  800 |     || | |    selected image           | |
| |[img]  | c.jpg    | Alps  | 2400 |     || | |                             | |
| |  ...  |          |       |      |     v| | +-----------------------------+ |
| +----------------------------------------+ |  Details                        |
|          QTableView (sortable)             |  File:   C:\Photos\a.jpg        |
|                                            |  Info:   1920 x 1080 | JPEG     |
|                                            |  Title:  [Beach day         ]   |
|                                            |  Tags:   [holiday, sea      ]   |
|                                            |  Rating: [4 /5 ^v]              |
|                                            |          [  Save Details  ]     |
+--------------------------------------------+---------------------------------+
| Scanning C:\Photos ...           30 image(s) [#####-----] 12/30  [Cancel]    |
+------------------------------------------------------------------------------+
                                                                 <- status bar
```

Dialogs: folder chooser, open/save file dialogs, error and warning message boxes, "remove this image?" confirmation, and "save changes?" on exit.

<!-- Add a screenshot of the finished app here and compare it with the wireframe -->

## 1.4 Architecture

I'm using **MVC adapted to Qt's model/view framework**:

```
        user clicks / types
               |
               v
     +-------------------+   custom signals   +----------------------+
     |  VIEW             | -----------------> |  CONTROLLER          |
     |  MainWindow       |                    |  MainController      |
     |  (widgets only)   | <----------------- |  (decides what to do)|
     +-------------------+   method calls     +----------------------+
               ^                                  |            |
               | Qt model/view                    |            | starts, cancels
     +-------------------+                        v            v
     | ImageTableModel   |  reads   +----------------+   +------------------+
     | ImageFilterProxy  | -------> | MODEL          |   | WORKER (thread)  |
     +-------------------+          | ImageCatalogue |   | ScanWorker       |
                                    | ImageItem      |   | uses processing  |
                                    | processing.py  |   | functions        |
                                    +----------------+   +------------------+
```

- **Model** (`catalogue/model/`): plain Python with no Qt imports. It holds the data, the validation rules, search, save/load and the image processing functions. Because it has no GUI code it can be unit tested easily.
- **View** (`catalogue/views/main_window.py`): builds the widgets and shows what it is told to show. When the user does something it emits a custom signal such as `details_submitted(title, tags, rating)`. It makes no decisions.
- **Controller** (`catalogue/controller/main_controller.py`): listens to the view's signals, calls the model, starts and cancels the background worker, and tells the view what to display.
- **Qt table model + proxy** (`catalogue/views/image_table_model.py`): Qt's `QTableView` needs a `QAbstractTableModel`. Mine is a thin adapter that reads from `ImageCatalogue` and tells the view about changes. The search rule itself is `ImageCatalogue.matches()`, so the logic stays in the model.
- **Worker** (`catalogue/workers/scan_worker.py`): does the slow processing away from the GUI thread and reports back using signals.
