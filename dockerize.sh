docker build -t "$2"/flask-study:"$1" .
docker images
docker run --network host -e CI=true -d -p 127.0.0.1:5000:5000 --name flask-study "$2"/flask-study:"$1"
docker ps | grep -q flask-study
docker ps -aqf "name=flask-study$"
docker push "$2"/flask-study:"$1"
docker logs $(docker ps -aqf name=flask-study$)
curl localhost:5000 || docker logs $(docker ps -aqf name=flask-study$)
docker kill flask-study || echo "flask-study killed"
docker rm flask-study || echo "flask-study removed"
