#!/bin/bash

#Colorines y carpetas

carpeta="$HOME/.var/app/com.mcpelauncher.MCPELauncher/data/mcpelauncher/versions/current"
fileconf="$HOME/.var/app/com.mcpelauncher.MCPELauncher/data/mcpelauncher/games/com.mojang/minecraftpe/options.txt"
carpeta3="$HOME/.var/app/com.mcpelauncher.MCPELauncher/data/mcpelauncher"
FLATINS="0"

carpeta1com="$HOME/.local/share/mcpelauncher/versions/current"
fileconfcom="$HOME/.local/share/mcpelauncher/games/com.mojang/minecraftpe/options.txt"
carpeta3com="$HOME/.local/share/mcpelauncher"
COMINS="0"

ROJO='\033[0;31m'
VERDE='\033[0;32m'
BLANCO='\033[1;37m'
AMARILLO='\033[1;33m'

#Funcion eliminar version actual
function eliminar_ver(){
    if [ "$FLATINS" = 1 ]; then
        echo ""
        cd $HOME
        mkdir "MCPELauncher-OLD"
        mv "$carpeta" "$HOME/MCPELauncher-OLD"
    elif [ "$COMINS" = 1 ]; then
        echo ""
        cd $HOME
        mkdir "MCPELauncher-OLD"
        mv "$carpeta1com" "$HOME/MCPELauncher-OLD"
    else
        echo -e "${ROJO}Estas seguro que hay una version como ${AMARILLO}Current${BLANCO}?"
        echo ""
        break
    fi
    echo -e "${AMARILLO}La version vieja se movio a su directorio HOME en la carpeta ${VERDE}MCPELauncher-OLD"
    echo ""
}

#Funcion desactivar Vibrant Visuals
function desactivar_shader(){
    if [ "$FLATINS" = 1 ]; then
        echo ""
        sed -i 's/graphics_mode:2/graphics_mode:0/g' "$fileconf"
    elif [ "$COMINS" = 1 ]; then
        echo ""
        sed -i 's/graphics_mode:2/graphics_mode:0/g' "$fileconfcom"
    else
        echo "${ROJO}Usted no tiene una version instalada, instale una e intente de nuevo"
        break
    fi
}

#Tutorial para customSkin
function how_customskin(){
    echo -e "${AMARILLO}Instrucciones para importar tus skins personalizadas:${BLANCO}"
    echo ""
    echo "Paso 1: Tener tu skin o skines dentro de una carpeta (opcional)"
    echo -e "Paso 2: Usando una herramienta online, programa o app en San Google busca algo como:${AMARILLO} 'SKINPACK MAKER'${BLANCO}"
    echo -e "Paso 3: Al colocar todo y exportar te debe dejar un archivo ${AMARILLO}.mcpack${BLANCO}"
    echo -e "Paso 4: Arrastra ese archivo ${AMARILLO}.mcpack${BLANCO} a la ventana del juego como cualquier addon"
    echo "Paso 5: Cargar desde vestidor y aspecto clasico deberia estar tu pack con tus skines"
    echo ""
    echo -e "${VERDE}Listo :)"
}

clear

#Arranque BASH
if [ "$SHELL" = '/bin/bash' -o "$SHELL" = '/bin/zsh' ]; then
    echo -e "Actualmente esta usando ${VERDE}$SHELL ${BLANCO}es seguro"
else
    echo -e "Actualmente esta usando${AMARILLO} $SHELL ${BLANCO}que quizas pueda generar problemas lo mas recomendable es que ejecute con ${AMARILLO}Bash${BLANCO}"
fi
echo ""

#Inicio

echo -e "${AMARILLO}Bienvenido a las herramientas para MCPELauncher (by@PlaGaDev) ver0.3"
echo -e "${BLANCO}"

#COMPROBANTE DE VER
echo -e "${AMARILLO}MCPELauncher:"
echo -e "${BLANCO}"

if [ -d "$carpeta3" ]; then
    echo -e "Version FLATPAK: ${VERDE}INSTALADO"
    FLATINS="1"
else
    echo -e "${BLANCO}Version FLATPAK: ${ROJO}NO INSTALADO"
    FLATINS="0"
fi
if [ -d "$carpeta3com" ]; then
    echo -e "${BLANCO}Version COMPILADO: ${VERDE}INSTALADO"
    COMINS="1"
else
    echo -e "${BLANCO}Version COMPILADO: ${ROJO}NO INSTALADO"
    COMINS="0"
fi

echo -e "${BLANCO}"

#Seleccionar version
if [ "$FLATINS" = '1' -a "$COMINS" = '1' ]; then
    echo "Por favor seleccione la version a modificar"
    echo ""
    opcionesver=("Opcion 1 - Version FLATPAK" "Opcion 2 - Version COMPILADA")
    select opt in "${opcionesver[@]}"
        do
            case $REPLY in
            1)
                echo ""
                COMINS="0"
                echo -e "Modificando version ${AMARILLO}Flatpak"
                ;;
            2)
                echo ""
                FLATINS="0"
                echo -e "Modificando version ${AMARILLO}Compilada"
                ;;
            *)
                echo ""
                echo -e "{$ROJO}Version invalida"
                break
                ;;
        esac
        break
    done
    echo -e "${BLANCO}"
fi

#Selector de opcion (MENU)

echo "Escriba el numero de la opcion:"
echo ""
opciones=("Opcion 1 - Mover y eliminar la version actual de MCPELauncher" "Opcion 2 - Desactivar Shader Vibrant Visuals" "Opcion 3 - Instrucciones de como cargar una customskin")
select opt in "${opciones[@]}"
    do
        case $REPLY in
        1)
            clear
            echo -e "${AMARILLO}Desea mover y remover la version actual? (SUS MUNDOS Y CONFIGURACIONES ESTARAN INTACTAS)"
                echo -e "${BLANCO}"
                opciones2=("1 - Eliminar" "2 - Cancelar")
                select opt in "${opciones2[@]}"
                do
                    case $REPLY in
                        1)
                            echo -e "${AMARILLO}Eliminando version actual"
                            eliminar_ver
                            echo -e "{$BLANCO}Ya puede instalar la nueva APK ;)"
                            ;;
                        2)
                            echo -e "${ROJO}Cancelando..."
                            break
                            ;;
                        *)
                            echo "${ROJO}Opcion invalida..."
                            break
                            ;;
                        esac
                        break
                    done
                    ;;
        2)
            clear
            if command -v sed &> /dev/null; then
                echo -e "${VERDE}SED si esta instalado..."
                echo ""
                if [ -e "$fileconf" -o -e "$fileconfcom" ]; then
                    echo -e "${BLANCO}El archivo ${AMARILLO}options.txt ${BLANCO}esta disponible..."
                    echo ""
                    echo "Modificando..."
                    desactivar_shader
                    echo -e "${VERDE}Se ha desactivado el shader correctamente ya puede disfrutar ;)"
                else
                    echo -e "${ROJO}Esta seguro de que esta instalado?"
                    echo ""
                    echo -e "${ROJO}Por favor instale de nuevo el MCPELauncher con un APK x86_64 e intente de nuevo..."
                fi
            else
            echo -e "${ROJO}SED no esta instalado..."
            echo -e "${BLANCO}Por favor instale sed del repositorio de su distro e intente de nuevo..."
            fi
            ;;
        3)
            clear
            how_customskin
            ;;
        *)
            echo -e "${ROJO}Opcion invalida..."
            break
            ;;
        esac
        break
    done
