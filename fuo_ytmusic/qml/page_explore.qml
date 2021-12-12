import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ScrollView {
    clip: true
    anchors.fill: parent
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical.policy: ScrollBar.AsNeeded
    contentWidth: availableWidth

    ColumnLayout {
        spacing: 10
        anchors.fill: parent

        TabBar {
            id: categoryBar
            Layout.fillWidth: true

            TabButton {
                text: qsTr("For You")
            }
            TabButton {
                text: qsTr("Moods")
            }
            TabButton {
                text: qsTr("Genres")
            }
        }

        StackLayout {
            Layout.fillWidth: true
            currentIndex: categoryBar.currentIndex

            ButtonGroup {
                id: categoryGroup
            }

            Flow {
                spacing: 6
                Layout.fillWidth: true

                Repeater {
                    id: forYou
                    model: []
                    delegate: Button {
                        property string params: modelData.params
                        flat: true
                        text: modelData.title
                        checkable: true
                        ButtonGroup.group: categoryGroup
                        onClicked: playlists.model = explore_backend.category_playlists(params)
                    }
                }
            }

            Flow {
                spacing: 6
                Layout.fillWidth: true

                Repeater {
                    id: moods
                    model: []
                    delegate: Button {
                        property string params: modelData.params
                        flat: true
                        text: modelData.title
                        checkable: true
                        ButtonGroup.group: categoryGroup
                        onClicked: playlists.model = explore_backend.category_playlists(params)
                    }
                }
            }

            Flow {
                spacing: 6
                Layout.fillWidth: true

                Repeater {
                    id: genres
                    model: []
                    delegate: Button {
                        property string params: modelData.params
                        flat: true
                        text: modelData.title
                        checkable: true
                        ButtonGroup.group: categoryGroup
                        onClicked: playlists.model = explore_backend.category_playlists(params)
                    }
                }
            }

            Component.onCompleted: {
                let categories = explore_backend.categories()
                forYou.model = categories.forYou
                moods.model = categories.moods
                genres.model = categories.genres
            }
        }

         Flow {
            spacing: 10
            Layout.fillWidth: true
            Layout.topMargin: 1

            Repeater {
                id: playlists
                model: []
                delegate: ColumnLayout {
                    width: 120

                    Image {
                        Layout.fillWidth: true
                        source: modelData.cover
                        Layout.preferredWidth: 120
                        Layout.preferredHeight: 120
                        fillMode: Image.PreserveAspectFit
                        clip: true

                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                console.log(modelData.id)
                                explore_backend.goto_playlist(modelData.id, modelData.name, modelData.cover)
                            }
                        }
                    }

                    Text {
                        topPadding: 2
                        text: modelData.name
                        font.pixelSize: 12
                        font.bold: true
                        clip: true
                        Layout.preferredWidth: 120
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
        }
    }
}
