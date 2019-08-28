package main

import (
	"flag"
	"time"
	"bytes"
	//"encoding/json"
	"encoding/base64"
	"io/ioutil"
	"net/http"
	"fmt"
	"path/filepath"
	"os"
	"log"
	"strconv"
)

//1. Collect all yaml files
//2. Add uncollected to list
//3. For each not disrupted, disrupt
//4. Post results to CALDERA

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

func modify_files(files []string) []string{
	var successful_files []string
	for _,f := range files{ 
		file, err := os.OpenFile(f, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		if err != nil {
			log.Println(err)
		}
		defer file.Close()
		if _, err := file.WriteString("caldera wuz here\n"); err != nil {
			log.Println(err)
		} else{
			successful_files = append(successful_files, f)
		}
	}
	return successful_files
}

func post_results(server string, files[]string){

	address := fmt.Sprintf("%s/sand/results", server)
	fmt.Println("About to Post Results:")
	
	for _,f := range files{ 
		fmt.Println(string(f))
	}
	//data, _ := json.Marshal(map[string]string{"output": string(util.Encode(string(f))), "status": status})
	request(address, []byte("YOYO"))
}

func request(address string, data []byte) []byte {
	req, _ := http.NewRequest("POST", address, bytes.NewBuffer(Encode(data)))
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil
	}
	body, _ := ioutil.ReadAll(resp.Body)
	return Decode(string(body))
}

//Encode base64 encodes bytes
func Encode(b []byte) []byte {
	return []byte(base64.StdEncoding.EncodeToString(b))
}

// Decode base64 decodes a string
func Decode(s string) []byte {
	raw, _ := base64.StdEncoding.DecodeString(s)
	return raw
}

func runMission(server string, extension string) string {
	all_files := get_files("/", extension)
	new_files := find_new_files(all_files)
	successful_files := modify_files(new_files)
	post_results(server, successful_files)
	return "Mission Completed"
}


func main() {
	server := flag.String("server", "http://localhost:8888", "The FQDN of the server")
	duration := flag.String("duration", "10", "How long the mission should run (seconds)")
	extension := flag.String("extension", ".caldera", "What extension are we searching for")
	modified_files = make(map[string]bool)
	flag.Parse()
	fmt.Printf("Running mission for %s seconds, posting results to %s\n", *duration, *server)
	i, _ := strconv.Atoi(*duration)
	expires := time.Now().Add(time.Duration(i) * time.Second)
	for  ; time.Now().Sub(expires) < 0; {
		runMission(*server, *extension) 
	}
	fmt.Println("DONE WITH MISSION")
}

var key = "3TEU4UD15V29OBJB7U9HNCR2JPWL1U"