package main

import (
	"flag"
	"time"
	"fmt"
	"path/filepath"
	"os"
	"log"
)

//https://github.com/mitre/sandcat/blob/af68b3e0b087c01bf98caaa32847fec920c4aa1e/gocat/cleanup/cleanup.go 
//this is good file to show how stuff will work
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

// Set Difference: A - B
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

func modify_files(files []string){
	for _,f := range files{ 
		f, err := os.OpenFile(f, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		if err != nil {
			log.Println(err)
		}
		defer f.Close()
		if _, err := f.WriteString("caldera wuz here\n"); err != nil {
			log.Println(err)
		}
	}
}

func runMission(server string, extension string) string {
	//1. Collect all yaml files
	//2. Add uncollected to list
	//3. For each not disrupted, disrupt
	//4. Post results to CALDERA
	all_files := get_files("/", extension)
	new_files := find_new_files(all_files)
	modify_files(new_files)
	return "Mission Completed"
}


func main() {
	server := flag.String("server", "http://localhost:8888", "The FQDN of the server")
	duration := flag.String("duration", "60", "How long the mission should run (seconds)")
	extension := flag.String("extension", ".caldera", "What extension are we searching for")
	modified_files = make(map[string]bool)
	flag.Parse()
	//run for a duration of time. 
	fmt.Printf("Running mission for %s seconds against %s\n", *duration, *server)
	for { 
		runMission(*server, *extension) 
	}
}

var key = "3TEU4UD15V29OBJB7U9HNCR2JPWL1U"