mkdir sftp
mkdir sftp/result
rm -rf sftp/result/*
rm -rf raw
rm -rf encripted
for i in {a..z} ; do touch data/$i.txt ; echo $i > data/$i.txt ; done

