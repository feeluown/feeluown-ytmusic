import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15

ScrollView {
    clip: true
    anchors.fill: parent
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical.policy: ScrollBar.AsNeeded
    contentWidth: availableWidth

    Material.theme: explore_backend.is_dark ? Material.Dark : Material.Light

    background: Rectangle {
        color: Material.background
    }

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
                        onClicked: {
                            categoryBusy.running = true
                            playlists.model = explore_backend.load_playlists(params)
                        }
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
                        onClicked: {
                            categoryBusy.running = true
                            playlists.model = explore_backend.load_playlists(params)
                        }
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
                        onClicked: {
                            categoryBusy.running = true
                            playlists.model = explore_backend.load_playlists(params)
                        }
                    }
                }
            }

            Component.onCompleted: {
                explore_backend.categoriesLoaded.connect(categoriesLoaded)
                categoryBusy.running = true
                explore_backend.load_categories()
            }

            function categoriesLoaded(categories) {
                forYou.model = categories.forYou
                moods.model = categories.moods
                genres.model = categories.genres
                categoryBusy.running = false
            }
        }

         Flow {
            property int rowPadding: (width + spacing) % (120 + spacing)

            id: playlistsFlow
            spacing: 10
            Layout.fillWidth: true
            Layout.topMargin: 1
            leftPadding: rowPadding / 2

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
                            onClicked: explore_backend.goto_playlist(modelData.id, modelData.name, modelData.cover)
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
                        color: Material.foreground
                    }
                }
            }
        }

        BusyIndicator {
            id: categoryBusy
            running: false
            Layout.alignment: Qt.AlignHCenter
        }

        function playlistsLoaded(ps) {
            playlists.model = ps
            categoryBusy.running = false
        }

        Component.onCompleted: {
            explore_backend.playlistsLoaded.connect(playlistsLoaded)
        }
    }
}
