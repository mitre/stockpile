package main

import (
	"flag"
	"time"
	"bytes"
	"strings"
	"encoding/json"
	"encoding/base64"
	"io/ioutil"
	"net/http"
	"fmt"
	"path/filepath"
	"os"
	"log"
	"strconv"
)

var iteration = 60
var modified_files map[string]bool

func get_files(searchpath string, extension string) []string{
	var files []string
	err := filepath.Walk(searchpath, func(path string, info os.FileInfo, err error) error {
		if filepath.Ext(path) == extension{
			files = append(files, path)
		}
        return nil
    })
    if err != nil {
        panic(err)
    }
	return files
}

func find_new_files(files []string) []string {
	var files_to_modify []string
	for _, file := range files{
		_, ok := modified_files[file]
		if ok == false{
			modified_files[file]=true
			files_to_modify = append(files_to_modify, file)
		} 
	}
	return files_to_modify
}

func modify_files(files []string, message string) []string{
	var successful_files []string
	for _,f := range files{ 
		file, err := os.OpenFile(f, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		if err != nil {
			log.Println(err)
		}
		defer file.Close()
		if _, err := file.WriteString(message); err != nil {
			log.Println(err)
		} else{
			successful_files = append(successful_files, f)
		}
	}
	return successful_files
}

func post_results(server string, files[]string){
	address := fmt.Sprintf("%s/sand/results", server)
	for _,f := range files{ 
		fmt.Println(string(f))
	}
	results := strings.Join(files, ",")
	data, _ := json.Marshal(map[string]string{"modified_files": results})
	request(address, Encode(data))
}

func request(address string, data []byte) []byte {
	req, _ := http.NewRequest("POST", address, bytes.NewBuffer(data))
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil
	}
	body, _ := ioutil.ReadAll(resp.Body)
	return Decode(string(body))
}

func Encode(b []byte) []byte {
	return []byte(base64.StdEncoding.EncodeToString(b))
}

func Decode(s string) []byte {
	raw, _ := base64.StdEncoding.DecodeString(s)
	return raw
}

func runMission(server string, extension string, message string) string {
	all_files := get_files("/", extension)
	new_files := find_new_files(all_files)
	successful_files := modify_files(new_files, message)
	post_results(server, successful_files)
	return "Mission Completed"
}


func main() {
	server := flag.String("server", "http://localhost:8888", "The FQDN of the server")
	duration := flag.String("duration", "60", "How long the mission should run (seconds)")
	extension := flag.String("extension", ".caldera", "What extension are we searching for")
	message := flag.String("message", "caldera wuz here", "What message should be inserted into the files")

	modified_files = make(map[string]bool)
	flag.Parse()
	fmt.Printf("Running mission for %s seconds, posting results to %s\n", *duration, *server)
	i, _ := strconv.Atoi(*duration)
	expires := time.Now().Add(time.Duration(i) * time.Second)
	for  ; time.Now().Sub(expires) < 0; {
		fmt.Println("In mission loop...")
		runMission(*server, *extension, *message) 
	}
	fmt.Println("Done with mission")
}

var key = "3TEU4UD15V29OBJB7U9HNCR2JPWL1U"