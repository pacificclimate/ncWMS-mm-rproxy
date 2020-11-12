#!/bin/bash
users=$1
tiles=$2
ports=$3

let "concurrent = $users * 6"

number=$concurrent

if [ -z $ports ]
then
   ports='30510 30511 30512'
fi

declare -a bboxes=(
  "-137.5,52.50000000000001,-125.00000000000001,65"
  "-125.00000000000001,52.50000000000001,-112.5,65"
  "-137.5,65,-125.00000000000001,77.5"
  "-125.00000000000001,65,-112.5,77.5"
  "-137.5,40,-125.00000000000001,52.50000000000001"
  "-125.00000000000001,40,-112.5,52.50000000000001"
  "-150,65,-137.5,77.5"
  "-150,52.50000000000001,-137.5,65"
  "-137.5,77.5,-125.00000000000001,90"
  "-150,77.5,-137.5,90"
  "-125.00000000000001,77.5,-112.5,90"
  "-150,40,-137.5,52.50000000000001"
)
nb=${#bboxes[@]}

for port in $ports
do
    for ((ib=0; i<=nb; ib++))
    do
        bbox=${bboxes[$ib]}
        ab -n "$number" -c "$concurrent" "http://docker-dev01.pcic.uvic.ca:$port/dynamic/x?service=WMS&request=GetMap&layers=tasmean_aClimMean_anusplin_historical_19610101-19901231%2Ftasmean&styles=default-scalar%2Fx-Occam&format=image%2Fpng&transparent=true&version=1.1.1&logscale=false&numcolorbands=249&abovemaxcolor=black&belowmincolor=white&time=1977-07-02T00%3A00%3A00Z&colorscalerange=-5%2C15&leaflet=%5Bobject%20Object%5D&width=256&height=256&srs=EPSG%3A4326&bbox=$bbox" > "test.$port.$ib.out" && \
        echo "port $port, bbox $bbox" && \
        grep 'per second' "test.$port.$ib.out" &
    done
done
