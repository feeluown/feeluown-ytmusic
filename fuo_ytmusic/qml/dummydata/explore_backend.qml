import QtQuick 2.3

// 以下是模拟数据用于 qmlscene 加载
QtObject {
    QtObject {
        id: categories
        ListModel {
            id: forYou
            ListElement {
                title: "For You Playlist"
                params: "test for you params"
            }
        }
        ListModel {
            id: moods
            ListElement {
                title: "Moods Playlist"
                params: "Moods params"
            }
        }
        ListModel {
            id: genres
            ListElement {
                title: "Genres Playlist"
                params: "Genres params"
            }
        }
    }
}
